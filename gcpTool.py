#!/usr/bin/env python

import json
import os
import re
import subprocess
import sys
import time

import csv

import random, string

from datetime import datetime
from datetime import timedelta


class GCPTool:
    def __init__(self, server_name, project, zone):
        self.server_name = server_name
        self.project = project
        self.zone = zone

    def define_me(self):
        command = "echo server: %s; project: %s; zone: %s" % (
            self.server_name, self.project, self.zone)
        os.system(command)

    def ssh(self, user_id=None):
        if user_id:
            command = "gcloud compute ssh --project %s --zone %s "\
                  "--internal-ip %s@%s" % (
                      self.project, self.zone, user_id, self.server_name)
        else:
            command = "gcloud compute ssh --project %s --zone %s "\
                  "--internal-ip %s" % (
                      self.project, self.zone, self.server_name)
        print("logging in...")
        os.system(command)

    def start(self):
        command = "gcloud compute instances start --project %s --zone %s %s" % (
            self.project, self.zone, self.server_name)
        os.system(command)

    def stop(self):
        command = "gcloud compute instances stop --project %s --zone %s %s" % (
            self.project, self.zone, self.server_name)
        os.system(command)
 
    def attach_disk(self, disk, is_boot=False):
        if is_boot:
            command = "gcloud compute instances attach-disk --project %s "\
                      "--zone %s %s --disk=%s --boot --device-name=%s" % (
                          self.project, self.zone, self.server_name, disk, disk)
        else:
            command = "gcloud compute instances attach-disk --project %s "\
                      "--zone %s %s --disk=%s --device-name=%s" % (
                          self.project, self.zone, self.server_name, disk, disk)

        print('attaching %s to %s...' % (disk, self.server_name))
        os.system(command)

    def restore_disk(self, date, time, is_boot):
        # Get disks
        print('getting list of disks...')
        get_disk_cmd = 'gcloud compute disks list --filter="users:%s" '\
            '--format=json --project %s' % (self.server_name, self.project)
        disks = subprocess.getoutput(get_disk_cmd)
        disks = json.loads(disks)

        print('Choose disk to restore:') 
        for i, disk in enumerate(disks):
            print('%s - %s' % (i+1, disk['name']))

        val = input('Pick a number: ')
        try:
            val = int(val) - 1
        except ValueError:
            print("You pick a wrong number")
            sys.exit()

        if val < 0:
            print("You pick a wrong number")
            sys.exit()

        try:
            disk = disks[val]
        except IndexError:
            print("You pick a wrong number")
            sys.exit(1)

        disk_name = disk["name"]
        disk_size = disk["sizeGb"]
        disk_type = disk["type"]
        disk_labels = disk["labels"] if "labels" in disk else None
        disk_policies = disk["resourcePolicies"]

        # describe old disk
        command = "gcloud compute disks describe %s --project %s --zone %s --format=json" % (disk_name, self.project, self.zone)
        os.system(command)

        # snapshot filter
        if time:
            time_utc = int(time) + 4
            datetime = date + str(time_utc)
        else:
            datetime = date
            
        filter = "sourceDisk:" + disk_name + " AND name ~ " + datetime

        # Get Snapshot
        print('getting disk snapshot...')
        get_snapshot_cmd = 'gcloud compute snapshots list --project=%s '\
            '--filter="%s" --format="json"' % (self.project, filter)
        snapshot = subprocess.getoutput(get_snapshot_cmd)
        try:
            snapshot = json.loads(snapshot)
        except json.decoder.JSONDecodeError:
            print("No snapshot found!")
            sys.exit()

        if len(snapshot) == 0:
            print("No snapshot found")
            sys.exit()

        data = snapshot[0]
        snapshot_name = data["name"]
        snapshot_random_key = data["name"].split("-")[-1]

        # Detach old disk
        print('Detaching %s disk...' % disk_name)
        self.detach_disk(disk_name)

        # Delete old disk
        print('Deleting %s disk...' % disk_name)
        command = "gcloud compute disks delete %s --project %s --zone %s" % (disk_name, self.project, self.zone)
        os.system(command)

        print('creating disk via "%s" snapshot...' % snapshot_name)
        
        # Create new disk from snapshot
        
        # Format Disk Labels
        if disk_labels:
            gcp_label_list_format = ""
            disk_labels_len = len(disk_labels)
            ctr = 1
            for key, value in disk_labels.items():
                if ctr == disk_labels_len:
                    gcp_label_format = "%s=%s" % (key, value)
                else:
                    gcp_label_format = "%s=%s," % (key, value)

                gcp_label_list_format += gcp_label_format
                ctr += 1
                
            create_disk_cmd = "gcloud compute disks create %s " \
                "--project %s --zone %s " \
                "--size=%s " \
                "--source-snapshot=%s " \
                "--type=%s " \
                "--labels=%s" % (disk_name, self.project, self.zone, disk_size, snapshot_name, disk_type, gcp_label_list_format)
        else:
            create_disk_cmd = "gcloud compute disks create %s " \
                "--project %s --zone %s " \
                "--size=%s " \
                "--source-snapshot=%s " \
                "--type=%s " % (disk_name, self.project, self.zone, disk_size, snapshot_name, disk_type)

        os.system(create_disk_cmd)

        for policy_link in disk_policies:
            policy = policy_link.split('/')[-1]
            add_policy_cmd = "gcloud compute disks add-resource-policies %s " \
                "--project %s --zone %s " \
                "--resource-policies=%s " % (disk_name, self.project, self.zone, policy)
            os.system(add_policy_cmd)
            
        print("Disk %s has been created." % disk_name)

        # Attach new disk
        print("Attaching %s disk..." % disk_name)
        if is_boot:
            self.attach_disk(disk_name, is_boot=True)
        else:
            self.attach_disk(disk_name, is_boot=False)
        
        # describe new disk
        command = "gcloud compute disks describe %s --project %s --zone %s --format=json" % (disk_name, self.project, self.zone)
        os.system(command)
        
    def detach_disk(self, disk):
        # get server disk details
        command = "gcloud compute instances detach-disk --project %s "\
                  "--zone %s %s --disk=%s" % (
                      self.project, self.zone, self.server_name, disk)

        print('detaching %s from %s...' % (disk, self.server_name))
        os.system(command)

    def add_network_tag(self, tags):
        command = "gcloud compute instances add-tags --project %s "\
                  "--zone %s %s --tags=%s" % (
                      self.project, self.zone, self.server_name, tags)
        os.system(command)

    def remove_network_tag(self, tags=[]):
        command = "gcloud compute instances remove-tags --project %s "\
                  "--zone %s %s --tags=%s" % (
                      self.project, self.zone, self.server_name, tags)
        os.system(command)        

    def add_label(self, labels=[]):
        pass

    def remove_label(self, labels=[]):
        pass

    def modify_label(self, label):
        command = "gcloud compute instances update --project %s "\
                  "--zone %s %s --update-labels %s" % (
                      self.project, self.zone, self.server_name, label)
        os.system(command)

    def set_disk_auto_delete(self):
        get_disk_cmd = 'gcloud compute disks list --filter="users:%s" '\
            '--format=json --project %s' % (self.server_name, self.project)
        disks = subprocess.getoutput(get_disk_cmd) 
        disks = json.loads(disks)

        for disk in disks:
            print("Setting auto-delete on '%s' disk..." % disk['name'])
            command = "gcloud beta compute instances set-disk-auto-delete --project %s "\
                    "--zone %s %s --auto-delete --disk=%s" % (
                        self.project, self.zone, self.server_name, disk['name'])
            os.system(command)


class CommandLineTool:
    def __init__(self, args):
        self.args = args
        self.options = {
            'help': 'help',
            'ssh': self.ssh,
            'start': self.start,
            'stop': self.stop,
            'attach': self.attach_disk,
            'detach': self.detach_disk, 
            'restore': self.restore_disk,
            'get-status': self.get_server_status, 
            'add-tag': 'add_tag',
            'remove-tag': 'remove_tag',
            'update-label': self.update_label,
            'set-disk-auto-delete': self.set_disk_auto_delete,
            'decommission': self.decommission
        }
    
    def help(self):
        print("Come again!")

    def ssh(self):
        # initialization
        args = self.get_args()
        server = self.get_server()
        project = args['--project'] if '--project' in args.keys() else args['-p'] if '-p' in args.keys() else None
        user_id = args['--user'] if '--user' in args.keys() else None

        # get server details
        project, zone, server = self.get_server_details(server, project)
        
        # validation
        question = "\r\nServer: %s\r\nProject: %s\r\nZone:%s\r\n\
                    \r\nAre you sure you want to ssh on the above server?(y/n)" % (
                        server, project, zone
                    )
        val = input(question)
        self.yes_no_validation(val)

        # ssh
        gcp_tool = GCPTool(server, project, zone)
        gcp_tool.ssh(user_id)

    def start(self):
        # initialization
        args = self.get_args()
        server = self.get_server()
        project = args['--project'] if '--project' in args.keys() else args['-p'] if '-p' in args.keys() else None

        # get server details
        project, zone, server = self.get_server_details(server, project)

        # validation
        question = "\r\nServer: %s\r\nProject: %s\r\nZone:%s\r\n\
                    \r\nAre you sure you want to start above server?(y/n)" % (
                        server, project, zone
                    )
        val = input(question)
        self.yes_no_validation(val)

        gcp_tool = GCPTool(server, project, zone)
        gcp_tool.start()

    def stop(self):
        # initialization
        args = self.get_args()
        server = self.get_server()
        project = args['--project'] if '--project' in args.keys() else args['-p'] if '-p' in args.keys() else None

        # get server details
        project, zone, server = self.get_server_details(server, project)

        # validation
        question = "\r\nServer: %s\r\nProject: %s\r\nZone:%s\r\n\
                    \r\nAre you sure you want to stop above server?(y/n)" % (
                        server, project, zone
                    )
        val = input(question)
        self.yes_no_validation(val)

        gcp_tool = GCPTool(server, project, zone)
        gcp_tool.stop()
        
    def attach_disk(self):
        # filter
        required = [
            ['--disk', '-d']
        ]
        args = self.get_args()
        self.check_required_parameter(required, args)

        # initialization
        server = self.get_server()
        project = args['--project'] if '--project' in args.keys() else args['-p'] if '-p' in args.keys() else None
        disk = args['--disk'] if '--disk' in args.keys() else args['-d']
        is_boot = True if '--boot' in args.keys() else False

        project, zone, server = self.get_server_details(server, project)
        
        question = "\r\nServer: %s\r\nProject: %s\r\nZone:%s\r\n\
                    \r\nAre you sure you want to attach %s disk on above server?(y/n)" % (
                        server, project, zone, disk
                    )
        val = input(question)
        self.yes_no_validation(val)

        gcp_tool = GCPTool(server, project, zone)
        gcp_tool.attach_disk(disk,is_boot)

    def restore_disk(self):
        # filter
        required = [
            ['--date', '-D'],
        ]
        args = self.get_args()
        self.check_required_parameter(required, args)

        # initialization
        server = self.get_server()
        project = args['--project'] if '--project' in args.keys() else args['-p'] if '-p' in args.keys() else None
        date = args['--date'] if '--date' in args.keys() else args['-D']
        is_boot = True if '--boot' in args.keys() else False
        try:
            time = args['--time'] if '--time' in args.keys() else args['-T']
        except KeyError:
            time = None

        project, zone, server = self.get_server_details(server, project)
        
        question = "\r\nServer: %s\r\nProject: %s\r\nZone:%s\r\n\
                    \r\nAre you sure you want to restore disk on above server?(y/n)" % (
                        server, project, zone
                    )
        val = input(question)
        self.yes_no_validation(val)

        gcp_tool = GCPTool(server, project, zone)
        gcp_tool.restore_disk(date, time, is_boot)

    def detach_disk(self):
        # filter
        required = [
            ['--disk', '-d']
        ]
        args = self.get_args()
        self.check_required_parameter(required, args)

        # initialization
        server = self.get_server()
        project = args['--project'] if '--project' in args.keys() else args['-p'] if '-p' in args.keys() else None
        disk = args['--disk'] if '--disk' in args.keys() else args['-d']

        project, zone, server = self.get_server_details(server, project)
        
        question = "\r\nServer: %s\r\nProject: %s\r\nZone:%s\r\n\
                    \r\nAre you sure you want to detach %s disk on above server?(y/n)" % (
                        server, project, zone, disk
                    )
        val = input(question)
        self.yes_no_validation(val)

        gcp_tool = GCPTool(server, project, zone)
        gcp_tool.detach_disk(disk)

    def add_tag(self):
        pass

    def remove_tag(self):
        pass

    def update_label(self):
        # filter
        required = [
            ['--label', '-l']
        ]
        args = self.get_args()
        self.check_required_parameter(required, args)

        # initialization
        server = self.get_server()
        project = args['--project'] if '--project' in args.keys() else args['-p'] if '-p' in args.keys() else None
        label = args['--label'] if '--label' in args.keys() else args['-l']
        label_key, label_value = label.split("=")

        project, zone, server = self.get_server_details(server, project)
        
        question = "\r\nServer: %s\r\nProject: %s\r\nZone:%s\r\n\
                    \r\nAre you sure you want to update '%s' label on above server?(y/n)" % (
                        server, project, zone, label_key
                    )
        val = input(question)
        self.yes_no_validation(val)

        gcp_tool = GCPTool(server, project, zone)
        gcp_tool.modify_label(label)

    def set_disk_auto_delete(self):
        args = self.get_args()

        # initialization
        server = self.get_server()
        project = args['--project'] if '--project' in args.keys() else args['-p'] if '-p' in args.keys() else None

        project, zone, server = self.get_server_details(server, project)
        
        question = "\r\nServer: %s\r\nProject: %s\r\nZone:%s\r\n\
                    \r\nAre you sure you want to auto delete disks on above server?(y/n)" % (
                        server, project, zone
                    )
        val = input(question)
        self.yes_no_validation(val)

        gcp_tool = GCPTool(server, project, zone)
        gcp_tool.set_disk_auto_delete()

    def decommission(self):
        args = self.get_args()
        args_length = len(self.args)
        if args_length <= 2:
            print("Please provide servername/serverlist.")
            sys.exit()

        if ".csv" in self.args[2]:
            with open(self.args[2]) as csv_file:
                csv_reader = csv.reader(csv_file)

                print("Server List:")
                for row in csv_reader:
                    print(row[0])

                val = input("Are you sure to decommission above servers?(y/n)")
                self.yes_no_validation(val) 

            with open(self.args[2]) as csv_file:
                csv_reader = csv.reader(csv_file)

                for row in csv_reader:
                    project, zone, server = self.get_server_details(row[0], None)
                    print(
                        "\r\nServer: %s\r\nProject: %s\r\nZone:%s" % (
                            server, project, zone
                        )
                    )

                    self.decommission_steps(server, project, zone)
        else:
            server = self.args[2]
            project, zone, server = self.get_server_details(server, None)
        
            question = "\r\nServer: %s\r\nProject: %s\r\nZone:%s\r\n\
                        \r\nAre you sure you want to decommission above server?(y/n)" % (
                            server, project, zone
                        )
            val = input(question)
            self.yes_no_validation(val)

            self.decommission_steps(server, project, zone)

    def decommission_steps(self, server, project, zone):
        print("\r\n(%s) Starting Decommission steps..." % server)

        if "pr-cah" in project and ("lpec" in server or "lpil" in server or "lpoh" in server):
            days_before_termination = 14

        else:
            days_before_termination = 7
        
        today = datetime.now()
        days_before_termination_timedelta = timedelta(days=days_before_termination)
        decommission_date_datetime = today + days_before_termination_timedelta
        decommission_date = decommission_date_datetime.strftime("%Y%m%d")
        decommission_label = "resourcename=%s_termination_%s" % (server, decommission_date)
        
        gcp_tool = GCPTool(server, project, zone)
        gcp_tool.modify_label(decommission_label)
        gcp_tool.modify_label("autostart=none")
        gcp_tool.set_disk_auto_delete()

    def get_server_status(self):
        args_length = len(self.args)
        if args_length <= 2:
            print("Please provide server list.")
            sys.exit()

        server_list = self.args[2]

        with open(server_list,"r") as file:
            for instance_ids in file:
                instance_id = instance_ids.split()[0]

                with open("instancesList.txt","r") as file:
                    for line in file:
                        if re.search(instance_id, line):
                            server = line.split()[0].split('/')[5]
                            status = line.split()[2]
                            print("%s - %s" % (server, status))

    def get_server(self):
        args_length = len(self.args)
        if args_length <= 2:
            print("Please provide server name.")
            sys.exit()

        return self.args[2]

    def yes_no_validation(self, val):
        if val != 'y' and val != 'n':
            print("Wrong input")
            sys.exit(1)
        elif val == 'n':
            print("exiting...")
            sys.exit(1)

    def get_server_details(self, server, project):
        if project:
            return self.get_server_detail_via_gcloud(
                server, project
                )
        else:
            return self.get_server_detail_from_list(server)

    def get_server_detail_from_list(self, server):
        data = []
        server_details = []
        self.download_GCP_data()
        with open("instancesList.txt","r") as file:
            for line in file:
                if re.search(server, line):
                    data.append(line)
        if not data:
            print("Server not found!")
            sys.exit(1)

        for d in data:
            d_formatted = d.split()[0].split('/')
            server_details.append({
                'server': d_formatted[5],
                'zone': d_formatted[3],
                'project': d_formatted[1]
            })
        
        if len(server_details) == 1:
            return (
                server_details[0]['project'], server_details[0]['zone'], 
                server_details[0]['server']
                )

        question = "Multiple server entry detected. Choose from the following:\r\n"
        for i, detail in enumerate(server_details):
            line = "(%s) %s - %s - %s\r\n" % (
                i+1, detail['server'], detail['project'], detail['zone'])
            question += line

        val = input(question)
        try:
            val = int(val) - 1
        except ValueError:
            print("You pick a wrong number")
            sys.exit()

        if val < 0:
            print("You pick a wrong number")
            sys.exit()

        try:
            return (
                    server_details[val]['project'], server_details[val]['zone'], 
                    server_details[val]['server']
                    )
        except IndexError:
            print("You pick a wrong number")
            sys.exit(1)

    def get_server_detail_via_gcloud(self, server, project):
        command = 'gcloud compute instances describe %s '\
                  '--format="json(name,project,zone)" '\
                  '--project %s > server_detail.tmp' % (server, project)
        os.system(command)
        with open("server_detail.tmp","r") as file:
            for line in file:
                if re.search("zone", line):
                    data = line.split('/')
                    zone = data[8].split('"')[0]
                    project = data[6]

                elif re.search('"name":', line):
                    server = line.split('"')[3]
                    
        os.remove('server_detail.tmp')            
        return (project, zone, server)

    def download_GCP_data(self):
        epoch_time = os.path.getmtime('./instancesList.txt')
        current_time = time.time()
        # in minutes
        file_age = (current_time - epoch_time) * 0.0167

        if file_age > 60:
            print("Downloading instancesList.txt...")
            os.system("gsutil cp gs://372449746971-stor/instancesList.txt .")

    def get_args(self):
        args = {}
        args_length = len(self.args)        
        for i in range(3, args_length):
            try:
                if self.args[i] == '--boot':
                    key = self.args[i]
                    value = True
                    args.update({key: value})
                    continue

                elif self.args[i] == '--label':
                    key = self.args[i]
                    i += 1;
                    value = self.args[i]
                    args.update({key: value})
                    break

                elif self.args[i] == '-l':
                    key = self.args[i]
                    i += 1;
                    value = self.args[i]
                    args.update({key: value})
                    break

                key, value = self.args[i].split('=')
            except ValueError:
                print("Wrong command format")
                sys.exit(1)
                
            args.update({key: value})

        return args

    def check_required_parameter(self, required, args):
        for option in required:
            if option[0] not in args.keys() and option[1] not in args.keys():
                print("Missing parameter: %s or %s" % (option[0], option[1]))
                sys.exit()
        
        return True

    def execute(self):
        if len(self.args) == 1:
            self.help()
            return None
            
        if self.args[1] not in self.options.keys():
            print(self.args[1])
            self.help()
            return None

        self.options[self.args[1]]()

    @classmethod
    def run(cls, args):
        cli = cls(args)
        cli.execute()


if __name__ == "__main__":
    CommandLineTool.run(sys.argv)
