#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from subprocess import Popen, PIPE, call
from StringIO import StringIO
from shutil import copyfile
from time import sleep

import json
import argparse
import os
import massedit
import base64

regexes = [
    "re.sub('<IPHIERHIN>', '{sub}', line)",
    "re.sub('<COMMON>', '{sub}.ov.otto.de', line)",
    "re.sub('<LOADBALANCER>', '{sub}', line)"
]

servers_file = 'servers.json'
servers_map = dict()

with open(servers_file) as f:
    servers_map = json.load(f)


def subsitute(regex, subsitute, filepath, dry=True):
    """
    Führt einen Inline-Replace im angegeben File durch.
    !!! Im Regex muss das Substitut als {sub} angegeben werden, sonst kann .format
    die Ersetzung im Regulären Ausdruck nicht durchführen !!!
    !!! Benötigt das Modul 'massedit' !!!

    Example:
        input = "Hallo Welt, wie schön Du doch bist!"
        regex = "re.sub('Hallo Welt', '{sub}', input)"
        subsitute(regex, 'Hallo Universum', input)
        input = "Hallo Universum, wie schön Du doch bist!"

    :param regex: Regex-Pattern
    :param subsitute: Ersetzung
    :param filepath: Pfad zum File, in dem die Ersetzung durchgeführt werden soll
    :param dry: Bei True werden zunächst nur die potentiellen Änderungen angezeigt.
                Bei False wird die Ersetzung durchgeführt.
    :return: nothing
    """

    massedit.edit_files(
        [filepath],
        [regex.format(sub=subsitute)],
        dry_run=dry
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--env', nargs='*')
    parser.add_argument('-t', '--typ')

    return parser.parse_args()


def create_cert(server, env, csr_out):
    """
    1) Legt für den Server einen Output-Ordner an.
    2) Kopiert die openssl.cnf in den Output-Ordner des Servers zur späteren Ersetzung der Variablen (ip, common name, ...)
    3) Nslookup <server>
    4) Ersetzt Variablen in der openssl.cnf mit der Server IP, dem DNS Namen des Servers, DNS Name des Loadbalancers, ...
    5) Generiert einen CSR für den jeweiligen Server aus openssl.cnf.
    6) Erstellt zusätzliche eine base64-encodierte Variante des CSRs

    :param server: Name des Servers, für den ein CSR erstellt werden soll
    :param env: Environment
    :param csr_out: Output-Verzeichnis-Root
    :return: nothing
    """

    pwd = os.path.dirname(os.path.realpath(__file__))

    # 1)
    server_dir = os.path.join(pwd, csr_out, server)

    if not os.path.exists(server_dir):
        os.makedirs(server_dir)

    # 2)
    copyfile(
        os.path.join(pwd, 'openssl2.cnf'),
        os.path.join(server_dir, 'openssl.cnf')
    )

    # 3)
    cmd = [
        "nslookup",
        '{s}'.format(s=server)
    ]

    nslookup = Popen(cmd, stdin=PIPE, stdout=PIPE, close_fds=True)
    stdout = StringIO(nslookup.stdout.read())
    # die benötigte IP-Adresse steht in der fünften Zeile; die ersten zehn Zeichen der Zeile = Address:\s
    ip = stdout.readlines()[4][9:]
    stdout.close()

    # 4)
    subs = [ip.strip(), server, servers_map[env]["lb"]]

    for regex, sub in zip(regexes, subs):
        # falls die Umgebung keinen Loadbalancer hat, lösche die Zeile aus openssl.cnf
        if not servers_map[env]["lb"]:
            exp = "re.sub('DNS.2       = <LOADBALANCER>', '{sub}', line)"
            subsitute(exp, '', os.path.join(server_dir, 'openssl.cnf'), dry=False)

        subsitute(regex, sub, os.path.join(server_dir, 'openssl.cnf'), dry=False)

    # 5)
    openssl_cmd = [
        "./openssl.sh",
        "-o", csr_out,
        "-s", server
    ]

    Popen(openssl_cmd, stdout=PIPE, stdin=PIPE, stderr=PIPE, close_fds=True)
    # kurz schlafen, sonst findet das folgende open() das Cert-File nicht
    sleep(0.3)

    # 6)
    with open(os.path.join(server_dir, "{s}_cer.pem".format(s=server)), 'r') as f:
        with open(os.path.join(server_dir, "{s}_cer.base64".format(s=server)), 'w') as b64:
            b64.write(base64.b64encode(f.read()))


def main():
    csr_out = 'out'
    args = parse_args()

    # all environments
    if not args.env:
        print "creating for all environments"
        for env in servers_map:
            if not args.typ:
                print "creating for both app and inf servers"
                for server in (servers_map[env]["app"] + servers_map[env]["inf"]):
                    #create_cert(server, "test", csr_out)
                    pass
                return
            else:
                print "creating for ", args.typ
                for server in servers_map[env][args.typ]:
                    #create_cert(server, "test", csr_out)
                    pass
                return

    # multiple environments
    if len(args.env) > 1:
        print "creating for environments ", args.env
        for env in args.env:
            if not args.typ:
                print "creating for both app and inf servers"
                for server in (servers_map[env]["app"] + servers_map[env]["inf"]):
                    #create_cert(server, "test", csr_out)
                    pass
                return
            else:
                print "creating for ", args.typ
                for server in servers_map[env][args.typ]:
                    #create_cert(server, "test", csr_out)
                    pass
                return

    # just one environment
    if not args.typ:
        print "creating for environment ", args.env
        for server in (servers_map[args.env[0]]["app"] + servers_map[args.env[0]]["inf"]):
            create_cert(server, "test", csr_out)
        return
    else:
        print "creating for ", args.typ
        for server in servers_map[args.env[0]][args.typ]:
            print csr_out
            create_cert(server, "test", csr_out)
        return


if __name__ == '__main__':
    main()
