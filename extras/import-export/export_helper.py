import logging
from StringIO import StringIO
from anzu.httpclient import HTTPClient, HTTPError
from anzu.escape import xhtml_unescape
from lxml import etree
from hashlib import md5
from base64 import b64encode

__all__ = ['get_page', 'get_part_of_page', 'get_gravatar_for']

def get_page(url, charset='utf-8', decode=True):
	client = HTTPClient()
	try:
		response = client.fetch(url)
	except HTTPError, he:
		#logging.debug(he)
		logging.debug('HTTPError when loading "%s"', url)
		return None
	except Exception, e:
		logging.warn(e)
		return None
	if 200 <= response.code < 300:
		if 'charset=' in response.headers.get('content-type'):
			new_charset = response.headers.get('content-type').split('charset=')[1].strip()
			if new_charset.lower() != charset:
				logging.debug('charset for "%s" is reported as "%s"; override the default', url, charset)
				charset = new_charset
		if decode:
			return response.body.decode(charset)
		else:
			return response.body
	else:
		logging.error('cannot load address "%s" - response code is %s', url, response.code)
		return None

def get_part_of_page(url, xpath="//div[contains(@class,'entrybody')]", charset='utf-8'):
	page_contents = get_page(url, charset)
	if page_contents:
		tree = etree.parse(StringIO(page_contents), etree.HTMLParser())

		find_content = etree.XPath(xpath)
		entry = find_content(tree)

		if len(entry) > 0:
			return xhtml_unescape(etree.tostring(entry[0], pretty_print=True).strip())
		else:
			logging.error('xpath expression "%s" returned nothing on "%s" - modify it', xpath, url)
			return None
	else:
		return None

gravatar_cache = {}
def get_gravatar_for(email, size=80, rating='R', as_text=True):
	assert rating in ['G', 'PG', 'R', 'X']
	assert 1 <= size <= 512

	if not email in gravatar_cache:
		logging.debug('about to get gravatar for "%s"', email)
		email_md5 = md5(email).hexdigest()
		url = 'http://www.gravatar.com/avatar/%s?r=%s&s=%d&d=404' % (email_md5, rating, size)
		gravatar_cache[email] = get_page(url, decode=False)
	else:
		logging.debug('gravatar for email address "%s" has been found in cache', email)

	gravatar = gravatar_cache[email]
	if gravatar:
		if as_text:
			# gravatars are served as jpeg
			return 'data:image/jpeg;base64,'+b64encode(gravatar)
		else:
			return gravatr
	else:
		return None
