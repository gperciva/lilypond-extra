#!/usr/bin/env python

import sys
import os
import mailbox
import email
import datetime

from email.header import decode_header

try:
    mbox_filename = sys.argv[1]
except:
    # to create combined.mbox:
    # - download files from ftp://lists.gnu.org/bug-lilypond/
    # - cat 2011-04 2011-05 > combined.mbox
    mbox_filename = "combined.mbox"

# the official bug squad as printed in the CG
# First element is email address, next is name, replies, role
bug_squad = [
    ["Phil Holmes","Phil Holmes", 0, "bug"],
    ["colinghall","Colin Hall", 0, "bug"],
    ["ralphbug","Ralph", 0, "bug"],
    ["Eluze","Eluze", 0, "bug"],
    ["Marek","Marek", 0, "bug"],
    ["Brett","Brett", 0, "bug"],
    ["Colin Campbell","Colin Campbell", 0, "extra"],
    ["dak@gnu","David Kastrup", 0, "extra"],
    ["OHara","Keith O'Hara", 0, "extra"],
    ["LEMBERG","Werner Lemberg", 0, "extra"],
    ["pkx","James", 0, "extra"],
    ["apolline","Mike S", 0, "extra"],
    ["n.puttock","Neil", 0, "extra"],
    ["percival-music","Graham", 0, "extra"],
    ["Kainhofer","Reinhold", 0, "extra"],
    ["paconet","Francisco Vila", 0, "extra"],
]

bug_squad_name_lookup = {}
for i in range(len(bug_squad)):
    name = bug_squad[i][0]
    bug_squad_name_lookup[name] = i

def is_official(author):
    for member in bug_squad_name_lookup:
        if author.find(member) >= 0:
            return member
    return None

initial_emails = []
for message in mailbox.mbox(mbox_filename):
    # ignore automatic emails from googlecode.
    if message['from'].startswith('lilypond@googlecode.com'):
        continue
    # ignore replies to previous emails
    if message['references'] or message['subject'].lower().startswith("re:"):
        continue
    # everything else should get a response
    initial_emails.append(message)

less_24_hours = []
less_48_hours = []
late_answer = []
never_answer = []

for question in initial_emails:
    # ick, sorry
    question_date = datetime.datetime(*(
        email.utils.parsedate(question['date'])[:-2]))
    # look for a response
    replied = False
    for message in mailbox.mbox(mbox_filename):
        if message['references']:
            if message['references'].find(question['message-id']) >= 0:
                # if not in a squad, don't consider the reponse as
                # official.
                replier = is_official( message['from'] )
                if not replier:
# Uncomment this for a list of other repliers
#                    print message['from']
                    continue
                bug_squad[bug_squad_name_lookup[replier]][2] += 1
                answer_date = datetime.datetime(*(
                    email.utils.parsedate(message['date'])[:-2]))
                delta = answer_date - question_date
                if delta < datetime.timedelta(hours=24):
                    less_24_hours.append( (question, message) )
                elif delta < datetime.timedelta(hours=48):
                    less_48_hours.append( (question, message) )
                else:
                    late_answer.append( (question, message) )
                replied = True
                break
    if not replied:
        # ignore emails in the past X hours
        delta = datetime.datetime.now() - question_date
        #if delta > datetime.timedelta(hours=168):
        if delta > datetime.timedelta(hours=24):
            never_answer.append( (question) )


def reassemble_header(header):
    reassembled = ' '.join([
            unicode(h[0], h[1] or 'utf8').encode('utf8')
                for h in decode_header(header)
        ])
    return reassembled


def write_table(html_file, message, emails, color):
    html_file.write("<h3>%s</h3>\n" % message)
#   html_file.write("<p><a id=\"Click\" href=\"javascript:ShowContents();\">Click here to show file contents</a> </p>")
#   html_file.write("<div class=\"Contents\">")
    html_file.write("<table border=\"1\">")
    html_file.write("<tr><th> Initial email </th><th></th><th></th><th> Answer </th></tr>")
    if len(emails) > 0:
        if len(emails[0]) == 2:
            for email, answer in emails:
                html.write("<tr><td> %s </td><td> %s </td><td> %s </td> <td bgcolor=\"%s\">%s</td></tr>" % (
                    email['date'],
                    reassemble_header(email['subject']),
                    reassemble_header(email['from']),
                    color,
                    reassemble_header(answer['from'])
                ))
        else:
            for email in emails:
                html.write("<tr><td> %s </td><td> %s </td><td> %s </td> <td bgcolor=\"%s\">%s</td></tr>" % (
                    email['date'], email['subject'], email['from'], color, "NOBODY"
                ))
    html.write("</table>")
#   html_file.write("</div>")



html = open('maybe-missing-emails---%s.html' % mbox_filename.replace('.mbox',''), 'w')

html.write("""<html>
<head>
  <title>Maybe missing: %s</title>
  <meta http-equiv="Content-type" content="text/html; charset=UTF-8" />
</head>
<body>
""" % mbox_filename.replace('.mbox',''))
#html.write("""
#    <script type="text/javascript" >
#        function ShowContents()
#        {
#            if
#(document.getElementById("Click").innerHTML.indexOf("show") > -1)
#            {
#                document.getElementById("pnlContents").style.display
#= 'block';
#                document.getElementById("Click").innerHTML = "Hide
#file contents";
#            }
#            else
#            {
#                document.getElementById("pnlContents").style.display
#= 'none';
#                document.getElementById("Click").innerHTML =
#"Click here to show file contents";
#            }
#        }
#    </script>
#""")

total_initial_emails = float(len(less_24_hours) + len(less_48_hours)
    + len(late_answer) + len(never_answer))
html.write("""<p>This examines the mailing list archives and
counts the FIRST reply from an official Bug Squad member (plus a
few extra people.  It doesn't look at discussions after the first
reply, so if bug squad person A replies to say "sorry, I don't
understand" and then bug squad person B replies to say "it's fine,
I understand and I've added a tracker issue", then this script
counts it as a "handled email" by person A.</p>
<p>If there's interest, we could expand this script to handle
those cases, but the intent is just a quick glimpse at how things
are progressing.  It's not totally accurate.</p>
<p>Direct link to official archives: <a
href="http://lists.gnu.org/archive/html/bug-lilypond/">
http://lists.gnu.org/archive/html/bug-lilypond/</a>
</p>""")

html.write("<h3>%s</h3>\n" % "Summary")

html.write("""<p>\"Never replied\" includes some administrative
emails (that need no reply), so it's not always a bad thing to
have <emph>some</emph> emails in this category.</p>""")

html.write("<table border=\"1\">")
html.write("<tr><th> Response category </th><th> Number </th><th>Percent of total</th></tr>")
def add_row(html, text, values):
    PercentEmails = 0
    if total_initial_emails > 0:
        PercentEmails = 100.0*len(values)/total_initial_emails
    html.write("<tr><td> %s </td><td> %i </td> <td> %.2f%% </td></tr>" % (
        text, len(values), PercentEmails))

add_row(html, "Less than 24 hours", less_24_hours)
add_row(html, "24 to 48 hours", less_48_hours)
add_row(html, "More than 48 hours", late_answer)
add_row(html, "Never replied", never_answer)

html.write("</table>")


html.write("<h3>%s</h3>\n" % "Initial replies by person")
bug_squad_replies = 0
for name in bug_squad_name_lookup:
    bug_squad_replies += bug_squad[bug_squad_name_lookup[name]][2]

def compare(a,b):
    return cmp(b[2], a[2])

bug_squad.sort(compare)

html.write("<table border=\"1\">")
html.write("<tr><th> Name </th><th> Replies </th><th> Bug squad? </th><th>Percent of total</th></tr>")
def add_row_names(html, text, num, squad):
    html.write("<tr><td> %s </td><td> %i </td> <td> %s </td> <td> %.2f%% </td></tr>" % (
        text, num, squad, 100.0*num/bug_squad_replies))
for name in bug_squad:
    if name[2]>0:
        add_row_names(html, name[1], name[2], name[3]=="bug")
html.write("</table>")

html.write("<h3>%s</h3>\n" % "Bug squad replies")
html.write("<table border=\"1\">")
html.write("<tr><th> Name </th><th> Replies </th>")
for name in bug_squad:
    if name[3]=="bug":
        html.write("<tr><td> %s </td><td> %i </td></tr>" % (name[1], name[2]))
html.write("</table>")


write_table(html, "Less than 24 hours", less_24_hours, "LightGreen")
write_table(html, "24 to 48 hours", less_48_hours, "yellow")
write_table(html, "Later than 48 hours", late_answer, "OrangeRed")
write_table(html, "Never replied", never_answer, "black")


email_verified = {}
for message in mailbox.mbox(mbox_filename):
    if message['from'].startswith('lilypond@googlecode.com'):
        msgbody = message.get_payload()
        if msgbody.find("Status: Verified") >= 0:
            msglines = msgbody.splitlines()
            email = ""
            for line in msglines:
                if line.find("Comment") == 0:
                    words = line.split()
                    for word in words:
                        if word.find("@") > 0:
                            email = word[0:word.find("@")]
                            try:
                                email_verified[email] += 1
                            except KeyError:
                                email_verified[email] = 1

html.write("<h3>%s</h3>\n" % "Issue verification")
html.write("<table border=\"1\">")
html.write("<tr><th> Name </th><th> Issues verified </th>")
for mail in sorted(email_verified, key=email_verified.get, reverse=True):
    html.write("<tr><td> %s </td><td> %i </td></tr>" % (mail, email_verified[mail]))
html.write("</table>")

html.write("</body></html>")
html.close()



