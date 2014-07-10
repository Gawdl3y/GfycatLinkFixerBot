import configparser
import praw
from praw.errors import RateLimitExceeded
import re
import time
from threading import Thread

# Read the config file
config = configparser.ConfigParser()
config.read('GfycatLinkFixerBot.cfg')

# Connect to Reddit
r = praw.Reddit(user_agent = 'Gfycat Link Fixer Bot v1.1 by /u/Gawdl3y')
r.login(config.get('Reddit', 'username'), config.get('Reddit', 'password'))
print('Logged in to Reddit as ' + r.user.name)

class Search(object):
	pattern = re.compile('^https?://(zippy|fat|giant)\.gfycat\.com/([a-z]+)\.gif$', re.IGNORECASE)
	message = (
		'[Fixed Gfycat Link (HTML5 & GIF)](http://gfycat.com/{slug})\n\n'
		'*****\n'
		'[About](http://www.reddit.com/r/GfycatLinkFixerBot/wiki/index) | Problems? Message /u/Gawdl3y or post in /r/GfycatLinkFixerBot.'
	)

	def __init__(self, submission):
		self.submission = submission
		self.match = Search.pattern.match(submission.url)

	def run(self):
		if not self.has_posted():
			self.post()
		else:
			print('Already posted in thread: ' + self.submission.permalink)

	def has_posted(self):
		for comment in self.submission.comments:
			if comment.author.id == r.user.id:
				return True
		return False

	def post(self):
		while True:
			try:
				comment = self.submission.add_comment(Search.message.format(slug = self.match.group(2)))
				print('Posted comment: ' + comment.permalink)
				return
			except RateLimitExceeded as e:
				print('Rate limit exceeded; waiting {0} seconds to try again'.format(e.sleep_time))
				time.sleep(e.sleep_time)

def main():
	submissions = praw.helpers.submission_stream(r, 'all', limit = None)
	for submission in submissions:
		search = Search(submission)
		if search.match is not None:
			thread = Thread(target = search.run)
			thread.start()

if __name__ == '__main__':
	main()