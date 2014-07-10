import configparser
import logging
import praw
import re
import time
from praw.errors import APIException, RateLimitExceeded
from requests.exceptions import HTTPError, ConnectionError, Timeout
from socket import timeout
from threading import Thread

# Read the config file
config = configparser.ConfigParser()
config.read('GfycatLinkFixerBot.cfg')

# Set up the logger for the console
logger = logging.getLogger('GfycatLinkFixerBot')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt = config.get('Logging', 'format'), datefmt = config.get('Logging', 'dateformat'))
console_handler = logging.StreamHandler()
console_handler.setLevel(int(config.get('Logging', 'consolelevel')))
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Add the file handler to the logger
log_file = config.get('Logging', 'file').strip()
if log_file:
	file_handler = logging.FileHandler(log_file)
	file_handler.setLevel(int(config.get('Logging', 'filelevel')))
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)

# Connect to Reddit
r = praw.Reddit(user_agent = 'Gfycat Link Fixer Bot v1.2 by /u/Gawdl3y')
r.login(config.get('Reddit', 'username'), config.get('Reddit', 'password'))
logger.info('Logged in to Reddit as ' + r.user.name)

class Search(object):
	pattern = re.compile('^https?://(zippy|fat|giant)\.gfycat\.com/([a-z]+)\.gif$', re.IGNORECASE)
	message = (
		'[Fixed Gfycat Link (HTML5 & GIF)](http://gfycat.com/{slug})\n\n'
		'*****\n'
		'[About](http://www.reddit.com/r/GfycatLinkFixerBot/wiki/index) |\n'
		'[Banlist](http://www.reddit.com/r/GfycatLinkFixerBot/wiki/banlist) |\n'
		'[Code](https://github.com/Gawdl3y/GfycatLinkFixerBot) |\n'
		'[Subreddit](http://www.reddit.com/r/GfycatLinkFixerBot) |\n'
		'Owner: /u/' + config.get('General', 'owner') + '  \n'
		'Problems? Please message the owner or post in the subreddit.'
	)
	retry_sleep = config.get('General', 'retrytime')

	def __init__(self, submission):
		self.submission = submission
		self.match = Search.pattern.match(submission.url)

	def run(self):
		if not self.has_posted():
			self.post()
		else:
			logger.info('Already posted in thread: ' + self.submission.permalink)

	def has_posted(self):
		for comment in self.submission.comments:
			if comment.author.id == r.user.id:
				return True
		return False

	def post(self):
		while True:
			try:
				comment = self.submission.add_comment(Search.message.format(slug = self.match.group(2)))
				logger.info('Posted comment: ' + comment.permalink)
				return
			except RateLimitExceeded as e:
				logger.warning('Rate limit exceeded; retrying in ' + str(e.sleep_time) + ' seconds')
				time.sleep(e.sleep_time)
			except HTTPError as e:
				if e.code == 403:
					logger.error('Forbidden from posting comment: ' + self.submission.permalink)
					return
				else:
					logger.warning('API error when posting comment; retrying in ' + str(self.retry_sleep) + ' seconds: ' + self.submission.permalink)
					logger.warning(e)
					time.sleep(self.retry_sleep)
			except (ConnectionError, Timeout, timeout) as e:
				logger.warning('Connection error when posting comment; retrying in ' + str(self.retry_sleep) + ' seconds: ' + self.submission.permalink)
				logger.warning(e)
				time.sleep(self.retry_sleep)
			except APIException as e:
				logger.warning('API error when posting comment; retrying in ' + str(self.retry_sleep) + ' seconds: ' + self.submission.permalink)
				logger.warning(e)
				time.sleep(self.retry_sleep)

def main():
	submissions = praw.helpers.submission_stream(r, 'all', limit = None)
	for submission in submissions:
		search = Search(submission)
		if search.match is not None:
			thread = Thread(target = search.run)
			thread.start()

if __name__ == '__main__':
	main()