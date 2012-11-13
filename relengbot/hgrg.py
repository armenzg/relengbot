from rebooter import Win32Slave, WarningPolicy
import paramiko
import logging
logging.basicConfig()

username = 'cltbld'
passwords = []

def doit(hostname):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(WarningPolicy())
    for password in passwords:
        try:
            client.connect(hostname, username=username, password=password, allow_agent=False)
            break
        except KeyboardInterrupt:
            raise
        except:
            continue
    else:
        logging.error("Couldn't connect to %s", hostname)
        return 'down'
    s = Win32Slave(client, hostname)
    s.wait()
    hgrc = s.run_cmd(r"C:\mozilla-build\msys\bin\cat.exe C:\Users\cltbld\.hgrc")
    share = s.run_cmd(r"C:\mozilla-build\hg\hg.exe share")
    print hostname,
    if "share" in hgrc and "unknown command" not in share and 'create a new shared repo' in share:
        print "OK!"
        return True
    else:
        print "MISSING!"
        s.wait()
        s.run_cmd(r"C:\mozilla-build\msys\bin\bash.exe -c 'echo [extensions]' > C:\Users\cltbld\.hgrc")
        s.wait()
        s.run_cmd(r"C:\mozilla-build\msys\bin\bash.exe -c 'echo share ='  >> C:\Users\cltbld\.hgrc")
        s.wait()
        return 'missing'

#for h in down:
    #doit(h)

oldpw = []
for i in range(4, 85):
    hostname = "w64-ix-slave%02i.build.mozilla.org" % i
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(WarningPolicy())
    for password in passwords:
        try:
            client.connect(hostname, username=username, password=password, allow_agent=False)
            logging.info("%s has old pw", hostname)
            oldpw.append(hostname)
            break
        except KeyboardInterrupt:
            raise
        except:
            continue
    else:
        logging.error("Couldn't connect to %s", hostname)

print "old passwords"
print oldpw
