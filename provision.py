#!/usr/bin/env python

import os
import tarfile
import getopt
import sys
from subprocess import call
from urllib2 import urlopen, URLError, HTTPError

def wget(url, dest, filename):
    path = dest + filename
    try:
        call([
            "wget",
            "--ca-directory",
            "/etc/ssl/certs",
            "-P",
            dest,
            url
        ])

        return path
    except Exception as err:
        print "wget error: {err} -> {u}".format(err=err, u=url)

def extract(tar, dest):
    try:

        if not os.path.exists(dest):
            print "creating destination folder {d}".format(d=dest)
            try:
                call(["mkdir", "-p", dest])
            except Exception as err:
                "Error creating destination folder {d}: {e}".format(d=dest, e=err)

        call(["tar", "-xf", tar, "-C", dest])

        opt = tar.strip("/tmp/").strip(".tar.xz").strip(".tar.gz")
        return dest + "/" + opt

    except Exception as err:
        print "Error extracting {f}: {e}".format(f=zip, e=err)

def symlink(src, dest):
    try:
        call(["ln", "-s", src, dest])
    except Exception as err:
        print "Error creating symlink from {s} to {d}: {e}".format(s=src, d=dest, e=err)

def parseOpts(args):
    options     = "n:y:h"
    long_opts   = [
            "node-version=",
            "yarn-version=",
            "help"
        ]

    node_version = "v"
    yarn_version = "v"

    try:
        opts, args = getopt.getopt(args, options, long_opts)
    except getopt.GetoptError as err:
        print err
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif opt in ("-n", "--node-version"):
            if arg:
                node_version += arg
            else:
                print "node version not specified"
                usage()
                sys.exit(2)
        elif opt in ("-y", "--yarn-version"):
            if arg:
                yarn_version += arg
            else:
                print "yarn version not specified"
                usage()
                sys.exit(2)
        else:
            print "unrecognized option: {o}".format(o=opt)
            usage()
            sys.exit(2)

    return node_version, yarn_version

def usage():
    print "Usage: ./provision.py --node-version=9.0.0 --yarn-version=1.5.1"

def main():

    node_version, yarn_version = parseOpts(sys.argv[1:])

    node_url = "https://nodejs.org/dist/{v}/node-{v}-linux-x64.tar.xz".format(v=node_version)
    yarn_url = "http://github.com/yarnpkg/yarn/releases/download/{v}/yarn-{v}.tar.gz".format(v=yarn_version)

    nodejs_name = "node-" + node_version + "-linux-x64.tar.xz"
    print "downloading nodejs version {v} from {u}".format(v=node_version, u=node_url)
    nodejs_tar  = wget(node_url, "/tmp/", nodejs_name)
    nodejs_opt  = extract(nodejs_tar, "/opt/node")
    nodejs_bin  = nodejs_opt + "/bin/node"
    npm_bin     = nodejs_opt + "/bin/npm"
    symlink(nodejs_bin, "/usr/bin/node")
    symlink(npm_bin, "/usr/bin/npm")

    yarn_name = "yarn-" + yarn_version + ".tar.gz"
    print "downloading yarn version {v} from {u}".format(v=yarn_version, u=yarn_url)
    yarn_tar  = wget(yarn_url, "/tmp/", yarn_name)
    yarn_opt  = extract(yarn_tar, "/opt/yarn")
    yarn_bin  = yarn_opt + "/bin/yarn"
    symlink(yarn_bin, "/usr/bin/yarn")

    # add CA to yarn, needed when behind proxy
    try:

        call([
            "yarn",
            "config",
            "set",
            "cafile",
            "/etc/ssl/certs/ca-bundle.pem"
            ])

    except Exception as err:
        print "error at setting ca-file to yarn config: {e}".format(e=err)

if __name__ == "__main__":
    main()
