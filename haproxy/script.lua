local socket = require("socket")
local http = require("socket.http")
local ltn12 = require("ltn12")

core.Info("Hello HAProxy!\n")

-- User connected IP limitations will be in the last (ip_user_connected_list_items * flush_interval) secs.
local path_ips_list_count = 10
local ip_user_connected_list_items = 2
local flush_interval = 30 -- seconds
local connected_ip_log_interval = 10 * 60 -- seconds
local max_ips_cache_duration = 5 * 60 -- seconds

local function getTimestamp()
    return os.time(os.date("!*t"))
end

local max_ips_cache = {}
local last_flush = getTimestamp()
local last_connected_ip_log = getTimestamp()
local last_max_ips_cache_flush = getTimestamp()

local path_ips_list = {}
for i = 1, path_ips_list_count do
    path_ips_list[i] = {}
end



local function log(msg)
    core.Info(os.date('%Y-%m-%d %H:%M:%S') .. " " .. msg)
end

local function logWarn(msg)
    core.Warning(os.date('%Y-%m-%d %H:%M:%S') .. " " .. msg)
end

local function addToSet(set, key)
    set[key] = true
end

local function removeFromSet(set, key)
    set[key] = nil
end

local function setContains(set, key)
    return set[key] ~= nil
end


local getMaxIps = function(txn, username)
    if getTimestamp() - last_max_ips_cache_flush > max_ips_cache_duration then
        max_ips_cache = {}
        last_max_ips_cache_flush = getTimestamp()
    end
    
    if setContains(max_ips_cache, username) then
        log("Max ips for " .. username .. " is in cache: " .. max_ips_cache[username] .. "\n")
        return max_ips_cache[username]
    end

    local HOSTCONTROLLER_API_KEY = txn.f:env("HOSTCONTROLLER_API_KEY")

    local body = {}
    local r, msg = http.request { 
        url = "http://127.0.0.1:1000/api/maxIps?connId=" .. username,
        method = "GET",
        headers = { ["X-API-KEY"] = HOSTCONTROLLER_API_KEY },
        sink = ltn12.sink.table(body),
        create = function()
            local req_sock = socket.tcp()
            req_sock:settimeout(0.1, 't')
            return req_sock
        end
    }
    if r == nil then
        logWarn("Error while getting max ips for " .. username .. ": " .. msg)
        return 9999
    end
    log("Max ips for " .. username .. ": " .. table.concat(body))
    
    local max_ips = tonumber(table.concat(body))
    max_ips_cache[username] = max_ips
    return max_ips
end

local function getLength(set)
    local count = 0
    for _ in pairs(set) do
        count = count + 1
    end
    return count
end

-- Carrier-grade NAT ranges (ISPs that hand a real user a new IP on every
-- request/reconnect) are read from this file, one IPv4 CIDR per line
-- ("#" starts a comment). A request whose source IP falls inside one of
-- these ranges is counted, for connection-limit purposes, as coming from
-- the whole matching CIDR rather than from its individual IP - so a single
-- legit user isn't mistaken for many devices sharing an account.
local cgnat_ranges_file = "/usr/local/etc/haproxy/cgnat-ranges.lst"
-- Feature toggle written by the panel (advanced settings), default enabled
-- when the file is missing/empty. Content "0" disables the feature.
local cgnat_enabled_file = "/haproxy-files/lists/cgnat-enabled.lst"
local cgnat_ranges_reload_interval = 5 * 60 -- seconds
local cgnat_ranges = {}
local cgnat_enabled = true
local last_cgnat_ranges_reload = 0

local function ip_to_int(ip)
    local a, b, c, d = ip:match("^(%d+)%.(%d+)%.(%d+)%.(%d+)$")
    if a == nil then
        return nil
    end
    return tonumber(a) * 16777216 + tonumber(b) * 65536 + tonumber(c) * 256 + tonumber(d)
end

local function load_cgnat_ranges()
    local ranges = {}
    local f = io.open(cgnat_ranges_file, "r")
    if f == nil then
        return ranges
    end
    for line in f:lines() do
        line = line:gsub("#.*$", ""):gsub("^%s+", ""):gsub("%s+$", "")
        if line ~= "" then
            local ip_part, prefix_part = line:match("^([^/]+)/(%d+)$")
            local network = ip_part and ip_to_int(ip_part) or nil
            if network ~= nil and tonumber(prefix_part) ~= nil then
                table.insert(ranges, { network = network, prefix_len = tonumber(prefix_part), cidr = line })
            else
                logWarn("Ignoring invalid CIDR in cgnat-ranges.lst: '" .. line .. "'\n")
            end
        end
    end
    f:close()
    return ranges
end

local function load_cgnat_enabled()
    local f = io.open(cgnat_enabled_file, "r")
    if f == nil then
        return true
    end
    local content = f:read("*l")
    f:close()
    return content ~= "0"
end

local function reload_cgnat_ranges_if_needed()
    local now = getTimestamp()
    if now - last_cgnat_ranges_reload > cgnat_ranges_reload_interval then
        last_cgnat_ranges_reload = now
        cgnat_ranges = load_cgnat_ranges()
        cgnat_enabled = load_cgnat_enabled()
    end
end

-- Returns the key to use when counting this IP towards a user's connection
-- limit: the matching configured CGNAT CIDR, or the plain IP if none match.
local function get_ip_count_key(ip)
    reload_cgnat_ranges_if_needed()

    if not cgnat_enabled then
        return ip
    end

    local ip_int = ip_to_int(ip)
    if ip_int == nil then
        return ip -- not a parseable IPv4 address (e.g. IPv6): count as-is
    end

    for _, range in ipairs(cgnat_ranges) do
        local block_size = 2 ^ (32 - range.prefix_len)
        local range_start = range.network - (range.network % block_size)
        if ip_int >= range_start and ip_int < range_start + block_size then
            return range.cidr
        end
    end

    return ip
end

local whitelist_users = {}
local whitelist_domains = {}

local function flush_if_needed()
    local now = getTimestamp()
    if now - last_flush > flush_interval then
        last_flush = now
        
        -- rotate path_ips_list, and flush the newest 
        for i = path_ips_list_count, 2, -1 do
            path_ips_list[i] = path_ips_list[i - 1]
        end
        path_ips_list[1] = {}

        logWarn("Flushed path_ips\n")
    end
    if now - last_connected_ip_log > connected_ip_log_interval then
        last_connected_ip_log = now
        total_ips = 0
        logWarn("*** Connected ips ***\n")
        for username, ips in pairs(path_ips_list[path_ips_list_count]) do
            total_ips = total_ips + getLength(ips)
            logWarn("   " .. username .. " connected ips: " .. getLength(ips) .. "\n")
            -- for ip, _ in pairs(ips) do
            --     logWarn("      " .. ip .. "\n")
            -- end
        end
        logWarn("Total connected ips: " .. total_ips .. "\n")
        logWarn("***\n")
    end
end

local function auth_request(txn)
    txn:set_var("txn.auth_response_successful", true)
    local hostname = txn.f:req_hdr("Host")

    -- check if hostname is whitelisted
    if setContains(whitelist_domains, hostname) then
        log("Domain " .. hostname .. " is whitelisted\n")
        return
    end

    local user_ip = txn.f:src()
    local forwarded_ip = txn.f:req_hdr_ip("X-Forwarded-For", 1)

    -- check if X-Forwarded-For header is present
    if forwarded_ip ~= nil then
        -- log("X-Forwarded-For header is present: " .. forwarded_ip .. " for " .. user_ip .. "\n")
        user_ip = forwarded_ip
    else
        -- log("X-Forwarded-For header is not present for " .. user_ip .. "\n")
    end

    -- get http request path from Fetches class of haproxy
    local path = txn.f:path()
    path = string.gsub(path, "___", "/")

    -- get first part of path if path contains at least two slashes
    if string.find(path, "/", 2) ~= nil then
        local username = string.sub(path, 2, string.find(path, "/", 2) - 1)
        log("Fetch " .. username .. " (" .. path .. ") from '" .. user_ip .. "'\n")

        if setContains(whitelist_users, username) then
            log("User " .. username .. " is whitelisted\n")
            return
        end

        flush_if_needed()

        -- key used for connection counting: the raw IP, unless it falls in a
        -- configured CGNAT range, in which case the whole range counts as one
        local count_key = get_ip_count_key(user_ip)

        -- check if user is already in path_ips table, if not add a list of ips
        for i = 1, path_ips_list_count do
            if path_ips_list[i][username] == nil then
                path_ips_list[i][username] = {}
            end
        end
        
        -- check if user ip is already in path_ips table, if not add the ip to the list
        if not setContains(path_ips_list[1][username], count_key) then
            -- check if user has reached max number of ips
            local maxIps = getMaxIps(txn, username)
            if getLength(path_ips_list[ip_user_connected_list_items][username]) >= maxIps then
                logWarn("User " .. username .. " has reached max number of " .. maxIps ..  " ips. Will deny request from " .. user_ip .. " on " .. hostname .. "\n")
                txn:set_var("txn.auth_response_successful", false)
                return
            end

            for i = 1, path_ips_list_count do
                if not setContains(path_ips_list[i][username], count_key) then
                    addToSet(path_ips_list[i][username], count_key)
                end
            end
            log(username .. ": IP " .. user_ip .. " connected to " .. hostname .. " (counted as " .. count_key .. ")\n")
        end
    end
end


local function connected_ips_count(applet)
    local username = string.sub(applet.path, 2, string.find(applet.path, "/", 2) - 1)

    local response = "0"
    if path_ips_list[ip_user_connected_list_items][username] ~= nil then
        response = getLength(path_ips_list[ip_user_connected_list_items][username])
    end

    applet:set_status(200)
    applet:add_header("Content-Type", "text/plain")
    applet:add_header("Content-Length", string.len(response))
    applet:start_response()
    applet:send(response)
end

local function connected_ips_count_long(applet)
    local username = string.sub(applet.path, 2, string.find(applet.path, "/", 2) - 1)

    local response = "0"
    if path_ips_list[path_ips_list_count][username] ~= nil then
        response = getLength(path_ips_list[path_ips_list_count][username])
    end

    applet:set_status(200)
    applet:add_header("Content-Type", "text/plain")
    applet:add_header("Content-Length", string.len(response))
    applet:start_response()
    applet:send(response)
end

local function total_connected_ips_count(applet)
    total_ips = 0
    for username, ips in pairs(path_ips_list[ip_user_connected_list_items]) do
        total_ips = total_ips + getLength(ips)
    end
    
    local response = total_ips

    applet:set_status(200)
    applet:add_header("Content-Type", "text/plain")
    applet:add_header("Content-Length", string.len(response))
    applet:start_response()
    applet:send(response)
end

local function total_connected_ips_count_long(applet)
    total_ips = 0
    for username, ips in pairs(path_ips_list[path_ips_list_count]) do
        total_ips = total_ips + getLength(ips)
    end
    
    local response = total_ips

    applet:set_status(200)
    applet:add_header("Content-Type", "text/plain")
    applet:add_header("Content-Length", string.len(response))
    applet:start_response()
    applet:send(response)
end

local function total_connected_users_count(applet)
    local response = getLength(path_ips_list[ip_user_connected_list_items])

    applet:set_status(200)
    applet:add_header("Content-Type", "text/plain")
    applet:add_header("Content-Length", string.len(response))
    applet:start_response()
    applet:send(response)
end

local function total_connected_users_count_long(applet)
    local response = getLength(path_ips_list[path_ips_list_count])

    applet:set_status(200)
    applet:add_header("Content-Type", "text/plain")
    applet:add_header("Content-Length", string.len(response))
    applet:start_response()
    applet:send(response)
end 

core.register_service("connected-ips-count", "http", connected_ips_count)
core.register_service("connected-ips-count-long", "http", connected_ips_count_long)
core.register_service("total-connected-ips-count-long", "http", total_connected_ips_count_long)
core.register_service("total-connected-ips-count", "http", total_connected_ips_count)
core.register_service("total-connected-users-count-long", "http", total_connected_users_count_long)
core.register_service("total-connected-users-count", "http", total_connected_users_count)
core.register_action("auth-request", { "http-req" }, auth_request, 0)
