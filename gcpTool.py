#!/usr/bin/env python

import os
import re
import sys
import time


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
                      "--zone %s %s --disk=%s --boot" % (
                          self.project, self.zone, self.server_name, disk)
        else:
            command = "gcloud compute instances attach-disk --project %s "\
                      "--zone %s %s --disk=%s" % (
                          self.project, self.zone, self.server_name, disk)

        print('attaching %s to %s...' % (disk, self.server_name))
        os.system(command)

    def detach_disk(self, disk):
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

    def modify_label(self, label={}):
        pass


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
            'add-tag': 'add_tag',
            'remove-tag': 'remove_tag',
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
