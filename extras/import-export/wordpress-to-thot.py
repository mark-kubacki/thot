#!/bin/env python
from os import getlogin, makedirs, path, utime
from datetime import datetime
import codecs
import logging
import re
import time

import MySQLdb as mdb
import yaml
import pytz

from anzu.options import parse_command_line, enable_pretty_logging
from anzu.escape import xhtml_unescape
from export_helper import get_page, get_part_of_page, get_gravatar_for

try:
	from collections import OrderedDict
except:
	from thot.utils import OrderedDict

enable_pretty_logging()
parse_command_line()

list_type = type([])
GMT = pytz.timezone('GMT')
# current user/system timezone
build_tz = pytz.timezone(time.strftime("%Z", time.gmtime()))
plugin = re.compile(r'\[\w')

print "MySQL connection data."
mysql_conn = {
	'host':   raw_input("  host [localhost]: ") or "localhost",
	'db':     raw_input("  database [%s_blog]: " % getlogin()) or getlogin()+"_blog",
	'user':   raw_input("  mysql username [%s]: " % getlogin()) or getlogin(),
	'passwd': raw_input("  password: ") or None,
}
wp_prefix = raw_input("  table prefix [wp_]: ") or "wp_"

con = mdb.connect(**mysql_conn)
logging.info("Connection to MySQL has been established.")
cur = con.cursor()

## posts
cur.execute("SELECT COUNT(*) FROM %sposts WHERE post_type='post' and post_status='publish'" % wp_prefix)
number_posts = cur.fetchone()[0]

## comments
cur.execute("SELECT COUNT(*) FROM %scomments WHERE comment_approved='1';" % wp_prefix)
number_comments = cur.fetchone()[0]

## what shall we do?
print "You have %d published blog posts and %d approved comments." % (int(number_posts), int(number_comments))
print "Do you want to export..."
export_posts = (raw_input("  all posts? [y/N]") or "n") in ['Y', 'y', 'J', 'j']
if export_posts:
	screen_scrape_if_necessary = (raw_input("  .. screen scrape if necessary? [Y/n]") or "y") in ['Y', 'y', 'J', 'j']
export_comments = (raw_input("  all comments? [y/N]") or "N") in ['Y', 'y', 'J', 'j']
if export_comments:
	check_pingbacks = (raw_input("  .. check whether pingbacks still link to the page? [Y/n]") or "y") in ['Y', 'y', 'J', 'j']
	get_gravatar = (raw_input("  .. get gravatar images and store them in comments' files? [y/N]") or "n") in ['Y', 'y', 'J', 'j']
outdir = raw_input("Directory for exports? [<empty>]") or ""

if outdir and not path.exists(outdir):
	makedirs(outdir)

## posts
if export_posts:
	# authors
	cur.execute("""SELECT u.ID, u.user_email as 'email', u.display_name as 'name'
	FROM {0}users u
	WHERE EXISTS (SELECT * FROM {0}posts p WHERE p.post_author = u.ID LIMIT 1)""".format(wp_prefix))
	# """
	authors = {}
	for row in cur:
		data = dict(zip([c[0] for c in cur.description], row))
		authors[data['ID']] = {'name': data['name'], 'email': data['email']}
	logging.info("Number of authors: %d", len(authors))
	if len(authors) < 2:
		logging.info("Won't write author information to posts, because this is no multi-author installation. Which is very common and perfectly okay. ;-)")

	# tags and categories
	cur.execute(
	"""SELECT r.object_id, tt.taxonomy, t.name, t.slug
	FROM {0}terms t
		NATURAL JOIN {0}term_taxonomy tt
		JOIN {0}term_relationships r ON (r.term_taxonomy_id = tt.term_taxonomy_id)
		/* now come object_ids for existing posts */
		JOIN {0}posts p ON (r.object_id = p.ID)
	WHERE p.post_type='post' AND p.post_status='publish'""".format(wp_prefix))
	# """
	labels = {}
	for row in cur:
		data = dict(zip([c[0] for c in cur.description], row))
		if 'post_tag' == data['taxonomy']:
			data['taxonomy'] = 'tags'

		if not data['object_id'] in labels:
			labels[data['object_id']] = {data['taxonomy']: [data['name']]}
		else:
			if not data['taxonomy'] in labels[data['object_id']]:
				labels[data['object_id']][data['taxonomy']] = [data['name']]
			else:
				labels[data['object_id']][data['taxonomy']].append(data['name'])
	logging.info("Reading of all tags and categories has been successfull. We have'em for %d posts.", len(labels))

	# tags/category to slug translation
	termfile_path = path.join(outdir, '_terms.yml')
	if not path.exists(termfile_path):
		cur.execute("""SELECT t.name, t.slug
		FROM {0}terms t NATURAL JOIN {0}term_taxonomy tt
		WHERE tt.count > 0 AND t.name != t.slug""".format(wp_prefix))
		# """
		terms = [{'term': row[0], 'slug': row[1]} for row in cur]
		logging.debug('%d terms have been found', len(terms))
		with codecs.open(termfile_path, 'wb', encoding='utf-8') as termfile:
			termfile.write(yaml.safe_dump(terms, default_flow_style=False))
	else:
		logging.info('A termfile already exists. Will skip creating a new one.')

	# the actual posts
	cur.execute(
	"""SELECT ID, post_author, post_date as 'date', post_content as 'content', post_title as 'title', comment_status, ping_status, post_name as 'cruft', post_modified as 'last_modified', post_modified_gmt, post_excerpt as 'excerpt', guid as 'old_path'
	FROM %sposts
	WHERE post_type='post' and post_status='publish'""" % wp_prefix)
	# """
	for row in cur:
		post = dict(zip([c[0] for c in cur.description], row))
		postfile_path = path.join(outdir, str(post['date'].year), "%02d" % post['date'].month, post['cruft']+'.html')
		if path.exists(postfile_path):
			logging.warn('skipping "%s" (already exists or name conflict)', postfile_path)
			continue
		logging.debug('working on "%s"', postfile_path)
		### post['template'] = 'post.mak'
		# We assume that 'post_date' aka 'date' will be in the same timezone as in the old blog.
		# Therefore it doesn't get localized.
		post['post_modified_gmt'] = GMT.localize(post['post_modified_gmt'])
		atime = mtime = int(time.mktime(post['post_modified_gmt'].astimezone(build_tz).timetuple()))
		del post['post_modified_gmt']
		# add category, tags and author
		if post['ID'] in labels:
			post.update(labels[post['ID']])
			if 'category' in post and list_type == type(post['category']) and 1 == len(post['category']):
				post['category'] = post['category'][0]
		if len(authors) >= 2:
			if post['post_author'] in authors:
				post['author'] = authors[post['post_author']]
			else:
				logging.warn('author with ID %d is unknown; post "%s" will have no author', post['post_author'], postfile_path)
		del post['post_author']
		del post['ID']
		# remove fields which are empty or unnecessary
		if not post['excerpt']: del post['excerpt']
		for k in ['comment_status', 'ping_status']:
			if k in post and 'open' == post[k]:
				del post[k] # comments: open -- already the default
			else:
				post[k] = 'closed'
		# If the post contains markup for plugins its contents habe to be fetched from the old WP site, because this tool cannot run them.
		if screen_scrape_if_necessary and plugin.search(post['content']):
			logging.info('post "%s" contains markup for plugins, therefore we will screen scrape it', postfile_path)
			content = get_part_of_page(post['old_path'])
		else:
			logging.debug('post "%s" seems not to have any plugin-generated content', postfile_path)
			content = post['content'].decode('utf-8')
		del post['content']
		del post['old_path']
		# write post to file
		for target_dir in [path.join(outdir, str(post['date'].year)), path.join(outdir, str(post['date'].year), "%02d" % post['date'].month)]:
			if not path.exists(target_dir):
				makedirs(target_dir)
		with codecs.open(postfile_path, 'wb', encoding='utf-8') as postfile:
			del post['cruft']
			postfile.write(yaml.safe_dump(post, default_flow_style=False, explicit_start=True))
			postfile.write("---\n\n")
			postfile.write(content)
		utime(postfile_path, (atime, mtime))

## comments
if export_comments:
	cur.execute("""SELECT c.comment_ID as 'ID', c.comment_parent as 'parent_ID',
			      c.comment_author as 'author', c.comment_author_email as 'email', c.comment_author_url as 'author_url',
			      c.comment_date as 'date', c.comment_content as 'content',
			      c.user_id > 0 as 'is_user',
			      CASE c.comment_type WHEN 'pingback' THEN 'pingback' ELSE 'comment' END as 'type',
			      p.post_name, p.post_date, p.guid as 'old_path'
			FROM {0}comments c
			     JOIN {0}posts p ON (c.comment_post_ID=p.ID)
			WHERE c.comment_approved='1'
			      AND p.post_type='post' AND p.post_status='publish'
			ORDER BY p.ID ASC, c.comment_date ASC""".format(wp_prefix))
	# """
	comments_by_id = dict()
	threads = OrderedDict()
	for row in cur:
		comment = dict(zip([c[0] for c in cur.description], row))
		comment['content'] = xhtml_unescape(comment['content']).replace('\r', '')
		comment['postfile_path'] = path.join(outdir, str(comment['post_date'].year), "%02d" % comment['post_date'].month, comment['post_name']+'.comments')

		# author
		if comment['type'] == 'pingback':
			comment['title'] = xhtml_unescape(comment['author'])
			comment['source'] = comment['author_url']
			del comment['author_url']
			del comment['author']
			del comment['email']
			# pingback verification
			if check_pingbacks:
				logging.debug('about to load page "%s", which has been the source of a pingback', comment['source'])
				contents = get_page(comment['source'])
				old_path = '/'.join(['/', comment['old_path'].split('/', 3)[2], str(comment['post_date'].year), "%02d" % comment['post_date'].month, comment['post_name']])
				if contents and ('href="http:'+old_path in contents or 'href="https:'+old_path in contents):
					logging.debug('all is okay, pingback "%s" has been verified', comment['source'])
					comment['last_verified'] = build_tz.localize(datetime.now())
				else:
					logging.info('pingback from "%s" does not link to "%s" anymore and will be omitted', comment['source'], old_path)
					continue # = skip
		else:
			del comment['type']
			comment['author'] = {'name': comment['author'], 'email': comment['email'], 'url': comment['author_url'], 'is_user': comment['is_user'] in [1, '1', True]}
			if get_gravatar and comment['author']['email']:
				gravatar = get_gravatar_for(comment['author']['email'])
				if gravatar:
					comment['author']['avatar'] = gravatar
			if not comment['author']['url']: del comment['author']['url']
			if not comment['author']['email']: del comment['author']['email']
			if not comment['author']['is_user']: del comment['author']['is_user']
			del comment['email']
			del comment['author_url']
		del comment['is_user']
		del comment['old_path']

		# threads
		if comment['parent_ID']:
			if comment['parent_ID'] in threads:
				threads[comment['parent_ID']].append(comment['ID'])
				del comment['post_name']
				del comment['post_date']
				del comment['postfile_path']
			else:
				logging.warning('comment %d says it is a response to %d, but the latter does not precede it (comments file "%s")', comment['ID'], comment['parent_ID'], comment['postfile_path'])
				threads[comment['ID']] = list()
		else:
			threads[comment['ID']] = list()

		# comment by ID
		comments_by_id[comment['ID']] = comment
		del comment['ID']
		del comment['parent_ID']
	logging.info('%d comments in %d threads have been loaded.', len(comments_by_id), len(threads))

	# build comment tree
	def get_comment_by_id(id):
		comment = comments_by_id[id]
		if id in threads and len(threads[id]) > 0:
			comment['replies'] = [get_comment_by_id(reply_id) for reply_id in threads[id]]
		return comment

	comments_by_page = dict()
	for id in threads:
		comment = get_comment_by_id(id)
		postfile_path = comment['postfile_path']
		del comment['postfile_path']
		if not postfile_path in comments_by_page:
			comments_by_page[postfile_path] = list()
		comments_by_page[postfile_path].append(comment)

	# write comments to file(s)
	for postfile_path in comments_by_page:
		for target_dir in [path.join(outdir, str(comments_by_page[postfile_path][0]['post_date'].year)),
				   path.join(outdir, str(comments_by_page[postfile_path][0]['post_date'].year), "%02d" % comments_by_page[postfile_path][0]['post_date'].month)]:
			if not path.exists(target_dir):
				makedirs(target_dir)
		if path.exists(postfile_path):
			logging.warn('skipping "%s" (already exists or name conflict)', postfile_path)
			continue
		for c in comments_by_page[postfile_path]:
			del c['post_date']
			del c['post_name']
		with codecs.open(postfile_path, 'wb', encoding='utf-8') as postfile:
			postfile.write(yaml.safe_dump(comments_by_page[postfile_path], default_flow_style=False))

## end
if con:
	con.close()
