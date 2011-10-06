#!/usr/bin/env python

import sys
import re
import os.path

# API docs:
#   http://code.google.com/p/support/wiki/IssueTrackerAPIPython
import gdata.projecthosting.client
import gdata.projecthosting.data
import gdata.gauth
import gdata.client
import gdata.data
import atom.http_core
import atom.core

class PatchBot():
    client = gdata.projecthosting.client.ProjectHostingClient()

    # you can use mewes for complete junk testing
    #PROJECT_NAME = "mewes"
    PROJECT_NAME = "lilypond"

    username = None
    password = None

    def __init__(self):
        # both of these bail if they fail
        self.get_credentials()
        #self.login()

    def get_credentials(self):
        # TODO: can we use the coderview cookie for this?
        #filename = os.path.expanduser("~/.codereview_upload_cookies")
        filename = os.path.expanduser("~/.lilypond-project-hosting-login")
        try:
            login_data = open(filename).readlines()
            self.username = login_data[0]
            self.password = login_data[1]
        except:
            print "Could not find stored credentials"
            print "  %(filename)s" % locals()
            print "Please enter loging details manually"
            print
            import getpass
            print "Username (google account name):"
            self.username = raw_input().strip()
            self.password = getpass.getpass()

    def login(self):
        try:
            self.client.client_login(
                self.username, self.password,
                source='lilypond-patch-handler', service='code')
        except:
            print "Incorrect username or password"
            sys.exit(1)


    def update_issue(self, issue_id, description):
        issue = self.client.update_issue(
                self.PROJECT_NAME,
                issue_id,
                self.username,
                comment = description,
                labels = ["Patch-new"])
        return issue

    def get_patches(self):
        query = gdata.projecthosting.client.Query(
            canned_query='open',
            label='Patch-Review')
        feed = self.client.get_issues(self.PROJECT_NAME,
            query=query)
        return feed


    def do_countdown(self):
        issues = self.get_patches()
        for i, issue in enumerate(issues.entry):
            print i, '\t', issue.get_id(), '\t', issue.title.text


def test_countdown():
    patchy = PatchBot()
    patchy.do_countdown()

test_countdown()

