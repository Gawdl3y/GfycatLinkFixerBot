import configparser
import logging
import praw
import re
import time
from praw.errors import APIException, RateLimitExceeded
from requests.exceptions import HTTPError, ConnectionError, Timeout
from socket import timeout
from threading import Thread

VERSION = '1.5'

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
r = praw.Reddit(user_agent = 'Gfycat Link Fixer Bot v' + VERSION + ' by /u/Gawdl3y')
r.login(config.get('Reddit', 'username'), config.get('Reddit', 'password'))
logger.info('Logged in to Reddit as ' + r.user.name)

class Search(object):
	pattern = re.compile('^https?://(zippy|fat|giant)\.gfycat\.com/([a-z]+)\.gif$', re.IGNORECASE)
	message = (
		'[Fixed Gfycat Link (HTML5 & GIF)](http://gfycat.com/{slug})\n\n'
		'^v' + VERSION + ' ^|\n'
		'^[About](http://www.reddit.com/r/GfycatLinkFixerBot/wiki/index) ^|\n'
		'^[Banlist](http://www.reddit.com/r/GfycatLinkFixerBot/wiki/banlist) ^|\n'
		'^[Code](https://github.com/Gawdl3y/GfycatLinkFixerBot) ^|\n'
		'^[Subreddit](http://www.reddit.com/r/GfycatLinkFixerBot) ^|\n'
		'^[Owner](http://www.reddit.com/user/' + config.get('General', 'owner') + ')  \n'
		'^(Problems? Please message the owner or post in the subreddit.)'
	)
	retry_sleep = float(config.get('General', 'retrytime'))
	exclusions = config.get('Reddit', 'exclude').strip().lower().split()

	def __init__(self, submission):
		self.submission = submission
		self.match = Search.pattern.match(submission.url)

	def run(self):
		if self.should_post():
			self.post()
		else:
			logger.info('Already posted or excluded: ' + self.submission.permalink)

	def should_post(self):
		if self.submission.subreddit.display_name.lower() in self.exclusions:
			return False
		for comment in self.submission.comments:
			if comment.author.id == r.user.id:
				return False
		return True

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
				if e.response.status_code == 403:
					logger.error('Forbidden from posting comment: ' + self.submission.permalink)
					return
				else:
					logger.warning('HTTP error when posting comment; retrying in ' + str(self.retry_sleep) + ' seconds: ' + self.submission.permalink)
					logger.warning(e)
					time.sleep(self.retry_sleep)
			except (ConnectionError, Timeout, timeout) as e:
				logger.warning('Connection error when posting comment; retrying in ' + str(self.retry_sleep) + ' seconds: ' + self.submission.permalink)
				logger.warning(e)
				time.sleep(self.retry_sleep)
			except APIException as e:
				if e.error_type == 'DELETED_LINK':
					logger.warning('Link deleted when posting comment: ' + self.submission.permalink)
					return
				else:
					logger.warning('API error when posting comment; retrying in ' + str(self.retry_sleep) + ' seconds: ' + self.submission.permalink)
					logger.warning(e)
					time.sleep(self.retry_sleep)

def main():
	submissions = praw.helpers.submission_stream(r, config.get('Reddit', 'subreddit'), limit = None)
	for submission in submissions:
		search = Search(submission)
		if search.match is not None:
			thread = Thread(target = search.run)
			thread.start()

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass