from datetime import datetime, timedelta
from pymongo import MongoClient
from . import config

def register_data(user_id, domain, domain_dns, protocol):
    # print(f"Health check from {user_id} for {protocol}://{domain} ({domain_dns})")

    # save to database
    client = MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    health_checks_raw = db.health_checks_raw
    health_checks_raw.insert_one({
        'user_id': user_id,
        'protocol': protocol,
        'domain': domain,
        'domain_dns': domain_dns,
        'timestamp': datetime.utcnow(),
    })

def parse():
    client = MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    health_checks_raw = db.health_checks_raw

    # ensure index exists for timestamp and domain
    print("Health check parse: creating indexes")
    health_checks_raw.create_index('timestamp')
    health_checks_raw.create_index('domain')
    health_checks_raw.create_index('domain_dns')
    health_checks_raw.create_index('protocol')
    health_checks_raw.create_index([('domain', 1), ('domain_dns', 1), ('protocol', 1), ('timestamp', 1)])

    # remove data older than 1 day
    print("Health check parse: removing old data")
    health_checks_raw.delete_many({
        'timestamp': {
            '$lt': datetime.utcnow() - timedelta(days=1)
        }
    })

    interval = timedelta(hours=3)
    start_time = datetime.utcnow() - timedelta(days=1) - interval
    start_time = start_time.replace(hour=start_time.hour - (start_time.hour % 3), minute=0, second=0, microsecond=0)
    final_time = datetime.utcnow()

    while start_time + interval < final_time:
        start_time += interval
        end_time = start_time + interval

        print(f"Health check parse: parsing from {start_time} to {end_time}")

        oldest_timestamp = health_checks_raw.find_one(sort=[('timestamp', 1)])['timestamp']

        # get distinct domains
        domains = health_checks_raw.distinct('domain')
        print(f"Health check parse: {len(domains)} domains")

        hit_counts = {}

        # get first timestamp for each domain, if it's not older than 23 hours, skip that domain
        for domain in domains:
            # first_timestamp_entry = health_checks_raw.find_one({
            #     'domain': domain,
            #     'timestamp': {
            #         '$gt': start_time,
            #         '$lt': end_time,
            #     }
            # }, sort=[('timestamp', 1)])
            # if first_timestamp_entry is None or first_timestamp_entry['timestamp'] > oldest_timestamp + timedelta(hours=1):
            #     print(f"Health check parse: {domain} skipped")
            #     continue

            # # get count of health checks received for domain
            # hit_counts[domain] = health_checks_raw.count_documents({
            #     'domain': domain
            # })

            # get distinct domain_dnses and protocols for domain
            domain_dnses = health_checks_raw.distinct('domain_dns', {
                'domain': domain,
                'timestamp': {
                    '$gt': start_time,
                    '$lt': end_time,
                }
            })
            protocols = health_checks_raw.distinct('protocol', {
                'domain': domain,
                'timestamp': {
                    '$gt': start_time,
                    '$lt': end_time,
                }
            })

            for domain_dns in domain_dnses:
                for protocol in protocols:
                    # get count of health checks received for domain, domain_dns, protocol
                    hit_counts[(domain, domain_dns, protocol)] = health_checks_raw.count_documents({
                        'domain': domain,
                        'domain_dns': domain_dns,
                        'protocol': protocol,
                        'timestamp': {
                            '$gt': start_time,
                            '$lt': end_time,
                        }
                    })
            
        if len(hit_counts) == 0:
            print("Health check parse: no domains to process")
            continue

        # get success rate for each domain
        max_hits_per_protocol = {}
        for domain, domain_dns, protocol in hit_counts:
            if not protocol in max_hits_per_protocol:
                max_hits_per_protocol[protocol] = 0
            max_hits_per_protocol[protocol] = max(max_hits_per_protocol[protocol], hit_counts[(domain, domain_dns, protocol)])

        for protocol in set(max_hits_per_protocol.keys()):
            if max_hits_per_protocol[protocol] < 10:
                print(f"Health check parse: skipped {protocol} because not enough data")
                del max_hits_per_protocol[protocol]

        print(max_hits_per_protocol)
        success_rates = {}
        for domain, domain_dns, protocol in hit_counts:
            if not protocol in max_hits_per_protocol:
                continue
            success_rates[(domain, domain_dns, protocol)] = hit_counts[(domain, domain_dns, protocol)] / max_hits_per_protocol[protocol]
            print(f"  {domain} ({domain_dns}) {protocol}: {hit_counts[(domain, domain_dns, protocol)]} hits, {success_rates[(domain, domain_dns, protocol)]} success rate")

        
        
        # save domain_success_rates to db
        health_checks = db.health_checks
        for domain, domain_dns, protocol in hit_counts:
            if not (domain, domain_dns, protocol) in success_rates:
                continue
            health_checks.update_one({
                'domain': domain,
                'domain_dns': domain_dns,
                'protocol': protocol,
                'time_slice': start_time,
            }, {
                '$set': {
                    'success_rate': success_rates[(domain, domain_dns, protocol)],
                    'calculate_timestamp': datetime.utcnow(),
                }
            }, upsert=True)


