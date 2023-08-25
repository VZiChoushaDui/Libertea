dataplaneapi {
  host = "0.0.0.0"
  port = 5555

  user "admin" {
    insecure = true
    password = {{API_PASSWORD}}
  }

  transaction {
    transaction_dir = "/tmp/haproxy"
  }
}

haproxy {
  config_file = "/etc/haproxy/haproxy.cfg"
  haproxy_bin = "/usr/sbin/haproxy"

  reload {
    reload_cmd  = "service haproxy reload"
    restart_cmd = "service haproxy restart"
    reload_delay = "5"
  }
}