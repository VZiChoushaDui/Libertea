local socket = require("socket")
local http = require("socket.http")
local ltn12 = require("ltn12")

core.Info("Hello HAProxy!\n")

local flush_interval = 150 -- seconds
local connected_ip_log_interval = 10 * 60 -- seconds

local function getTimestamp()
    return os.time(os.date("!*t"))
end

local last_flush = getTimestamp()
local last_connected_ip_log = getTimestamp()

local path_ips = {}
local path_ips_long = {}

local function log(msg)
    core.Info(os.date('%Y-%m-%d %H:%M:%S') .. " " .. msg)
end

local function logWarn(msg)
    core.Warning(os.date('%Y-%m-%d %H:%M:%S') .. " " .. msg)
end


local getMaxIps = function(txn, username)
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
    return tonumber(table.concat(body))
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

local function getLength(set)
    local count = 0
    for _ in pairs(set) do
        count = count + 1
    end
    return count
end

local whitelist_users = {}
local whitelist_domains = {}

local function flush_if_needed()
    local now = getTimestamp()
    if now - last_flush > flush_interval then
        last_flush = now
        path_ips_long = path_ips
        path_ips = {}
        logWarn("Flushed path_ips\n")
    end
    if now - last_connected_ip_log > connected_ip_log_interval then
        last_connected_ip_log = now
        total_ips = 0
        logWarn("*** Connected ips ***\n")
        for username, ips in pairs(path_ips_long) do
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
        log("X-Forwarded-For header is present: " .. forwarded_ip .. " for " .. user_ip .. "\n")
        user_ip = forwarded_ip
    else
        log("X-Forwarded-For header is not present for " .. user_ip .. "\n")
    end

    -- get http request path from Fetches class of haproxy
    local path = txn.f:path()

    -- get first part of path if path contains at least two slashes
    if string.find(path, "/", 2) ~= nil then
        local username = string.sub(path, 2, string.find(path, "/", 2) - 1)
        log("Fetch " .. username .. " (" .. path .. ") from '" .. user_ip .. "'\n")

        if setContains(whitelist_users, username) then
            log("User " .. username .. " is whitelisted\n")
            return
        end

        flush_if_needed()

        -- check if user is already in path_ips table, if not add a list of ips
        if path_ips[username] == nil then
            path_ips[username] = {}
        end
        if path_ips_long[username] == nil then
            path_ips_long[username] = {}
        end
        
        -- check if user ip is already in path_ips table, if not add the ip to the list
        if not setContains(path_ips[username], user_ip) then
            -- check if user has reached max number of ips
            local maxIps = getMaxIps(txn, username)
            if getLength(path_ips[username]) >= maxIps then
                logWarn("User " .. username .. " has reached max number of " .. maxIps ..  " ips. Will deny request from " .. user_ip .. " on " .. hostname .. "\n")
                txn:set_var("txn.auth_response_successful", false)
                return
            end

            addToSet(path_ips[username], user_ip)
            addToSet(path_ips_long[username], user_ip)
            log(username .. ": IP " .. user_ip .. " connected to " .. hostname .. "\n")
        end

        -- log(" Number of ips for " .. username .. ": " .. getLength(path_ips[username]) .. "\n")
    end
end


local function connected_ips_count(applet)
    local username = string.sub(applet.path, 2, string.find(applet.path, "/", 2) - 1)

    local response = "0"
    if path_ips_long[username] ~= nil then
        response = getLength(path_ips_long[username])
    end

    applet:set_status(200)
    applet:add_header("Content-Type", "text/plain")
    applet:add_header("Content-Length", string.len(response))
    applet:start_response()
    applet:send(response)
end

local function total_connected_ips_count(applet)
    total_ips = 0
    for username, ips in pairs(path_ips_long) do
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
    local response = getLength(path_ips_long)

    applet:set_status(200)
    applet:add_header("Content-Type", "text/plain")
    applet:add_header("Content-Length", string.len(response))
    applet:start_response()
    applet:send(response)
end

core.register_service("connected-ips-count", "http", connected_ips_count)
core.register_service("total-connected-ips-count", "http", total_connected_ips_count)
core.register_service("total-connected-users-count", "http", total_connected_users_count)
core.register_action("auth-request", { "http-req" }, auth_request, 0)
