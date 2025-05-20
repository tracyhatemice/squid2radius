squid2radius
============

squid2radius analyzes entries generated in the past 60 minutes (via `--seek_time` argument) in your squid `access.log` file, and reports usage information to a RADIUS server using `Accounting-Request` as defined in RFC 2866.

Installation
------------

### Clone Git repo

```bash
git clone https://github.com/tracyhatemice/squid2radius.git
```

### Install dependencies within virtual environmanet

```bash
cd squid2radius
python3 -m venv venv
source venv/bin/activate
# requires pyrad and hurry.filesize libraries to be installed
python3 -m pip install pyrad hurry.filesize
```

### Setup cronjob

Set up a cronjob that runs every hour.  **Need necessary permission to read squid access log.**

```bash
0 * * * * /usr/bin/env bash -c 'cd /home/user/squid2radius && source /home/user/squid2radius/venv/bin/activate && python3 ./squid2radius.py radius_server radius_secret' > /dev/null 2>&1
```

Changelog
-----------------
### v2.0

#### New behaviour

* add `Calling-Station-ID` attribute to the accounting data.
* add `--seek_time` argument, defaults to 60 minutes, which is helpful if the cronjob is set to run every hour.  See usage.
* replace `--no-rotation` arguement with `--rotation` arguement, and defaults not to rotate squid access log.
* set `--logfile_path` to optional, defaults to `/var/log/squid/access.log`

### v1.0

#### New dependency `hurry.filesize`

Note that an dependency `hurry.filesize` is required since Version 1.0.  Run 
`sudo pip2 install hurry.filesize` to install it.


Usage
-----

```
Usage: usage: squid2radius.py [-h] \
                              [--version] \
                              [--logfile_path LOGFILE_PATH] \
                              [--seek_time SEEK_TIME] \
                              [-p RADIUS_ACCT_PORT] \
                              [--radius-nasid RADIUS_NASID] \
                              [--squid-path SQUID_PATH] \
                              [--exclude-pattern EXCLUDE_PATTERN] \
                              [--dry-run] \
                              [--rotation] \
                              radius_server radius_secret
```

For instance, run like this if you have access log file at `/var/log/squid/access.log`, RADIUS server running at `localhost` with secret set to `testing123`:

```bash
sudo python3 squid2radius.py localhost testing123
```

It is certainly a good idea to make a cron job for this.

You should also read [SquidFaq/SquidLogs](http://wiki.squid-cache.org/SquidFaq/SquidLogs#access.log) to make sure your log files are in reasonable sizes.

### --exclude-pattern

If for some reason you need to prevent usage information of certain user from being sent to the RADIUS server, there is an argument for that!  Use `--exclude-pattern="(girl|boy)friend"` and squid2radius won't send usage of either your `girlfriend` or `boyfriend` to the RADIUS server.

### --dry-run

If the script is called with this argument, no data will be sent to the server.

### --seek_time

The script will read the squid access log file (using `--logfile_path` argument, defaults to `/var/log/squid/access.log`), filter the entries based on the specified time range (`--seek_time`), and then send the accounting data to the RADIUS server using the pyrad library.  Could be handy in combination with hourly cronjob.

### --rotation

Generally, rotating squid access log is not required as the script will only process the log entries within the specified time range (using `--seek_time` argument, defaults to 60, meaning read logs generated in the past 60 minutes.) 

If needed, you can add `--rotation` argument, so that squid2radius will call `squid -k rotate` to make squid rotate access log right after done counting usage data.  This may help to ensure usage data accuracy by not counting any log lines more than once next time you run it.

Note
----

The script assumes that you are using the default [Squid native access.log format](http://wiki.squid-cache.org/Features/LogFormat#squid) on first ten columns of your log file.  If you need custom columns, add them after the default ones.

Author, Copyright
----

squid2radius was written by [jiehanzheng](https://github.com/jiehanzheng/squid2radius) and updated for python3 compatibility among other minor changes by [tracyhatemice](https://github.com/tracyhatemice/squid2radius).

Copyright an license information can be found in the LICENSE.txt file.
