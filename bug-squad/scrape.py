#!/usr/bin/env python

import sys
import mailbox
import email
import datetime

try:
	mbox_filename = sys.argv[1]
except:
	# to create combined.mbox:
	# - download files from ftp://lists.gnu.org/bug-lilypond/
	# - cat 2011-04 2011-05 > combined.mbox
	mbox_filename = "combined.mbox"

# the official bug squad as printed in the CG
bug_squad = [
	"Colin",
	"Dmytro",
	"James Bailey",
	"Ralph",
	"Patrick",
	"Urs",
	"Kieren",
]

# people who occasionally act as "replacement" Bug Squad members
extra_squad = [
	"Phil Holmes",
	"Graham Percival",
	"Keith OHara",
	"Neil Puttock"
]

def is_official(author):
	for member in bug_squad + extra_squad:
		if author.find(member) >= 0:
			return member
	return None

bug_squad_initial_responses = {}
for name in bug_squad + extra_squad:
	bug_squad_initial_responses[name] = 0

initial_emails = []
for message in mailbox.mbox(mbox_filename):
	# ignore automatic emails from googlecode.
	if message['from'].startswith('lilypond@googlecode.com'):
		continue
	# ignore replies to previous emails
	if message['references'] or message['subject'].startswith("Re:"):
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
					continue
				bug_squad_initial_responses[replier] += 1
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

def write_table(html_file, message, emails, color):
	html_file.write("<h3>%s</h3>\n" % message)
#	html_file.write("<p><a id=\"Click\" href=\"javascript:ShowContents();\">Click here to show file contents</a> </p>")
#	html_file.write("<div class=\"Contents\">")
	html_file.write("<table border=\"1\">")
	html_file.write("<tr><th> Initial email </th><th></th><th></th><th> Answer </th></tr>")
	if len(emails) > 0:
		if len(emails[0]) == 2:
			for email, answer in emails:
				html.write("<tr><td> %s </td><td> %s </td><td> %s </td> <td bgcolor=\"%s\">%s</td></tr>" % (
					email['date'], email['subject'], email['from'], color, answer['from']
				))
		else:
			for email in emails:
				html.write("<tr><td> %s </td><td> %s </td><td> %s </td> <td bgcolor=\"%s\">%s</td></tr>" % (
					email['date'], email['subject'], email['from'], color, "NOBODY"
				))
	html.write("</table>")
#	html_file.write("</div>")


html = open('maybe-missing-emails.html', 'w')
html.write("<html><head></head><body>\n")
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
	html.write("<tr><td> %s </td><td> %i </td> <td> %.2f%% </td></tr>" % (
		text, len(values), 100.0*len(values)/total_initial_emails))

add_row(html, "Less than 24 hours", less_24_hours)
add_row(html, "24 to 48 hours", less_48_hours)
add_row(html, "More than 48 hours", late_answer)
add_row(html, "Never replied", never_answer)

html.write("</table>")


html.write("<h3>%s</h3>\n" % "Initial replies by person")
total_replies = sum([a for a in bug_squad_initial_responses.values()])

html.write("<table border=\"1\">")
html.write("<tr><th> Name </th><th> Replies </th><th>Percent of total</th></tr>")
def add_row_names(html, text, num):
	html.write("<tr><td> %s </td><td> %i </td> <td> %.2f%% </td></tr>" % (
		text, num, 100.0*num/total_replies))
for name in bug_squad:
	num_responses = bug_squad_initial_responses[name]
	add_row_names(html, name, num_responses)
for name in extra_squad:
	num_responses = bug_squad_initial_responses[name]
	add_row_names(html, name, num_responses)

html.write("</table>")


write_table(html, "Less than 24 hours", less_24_hours, "green")
write_table(html, "24 to 48 hours", less_48_hours, "yellow")
write_table(html, "Later than 48 hours", late_answer, "red")
write_table(html, "Never replied", never_answer, "black")

html.write("</body></html>")
html.close()


