<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en-us">
<head>
   <meta http-equiv="content-type" content="text/html; charset=utf-8" />
   <title>${ page['title'] }</title>
   <meta name="author" content="${ settings['author_name'] }" />

   <!-- syntax highlighting CSS -->
   <link rel="stylesheet" href="css/syntax.css" type="text/css" />

   <!-- Homepage CSS -->
   <link rel="stylesheet" href="css/screen.css" type="text/css" media="screen, projection" />
</head>
<body>

<div class="site">
  <div class="title">
    <a href="/">${ settings['author_name'] }</a>
  </div>

  ${next.body()}
  
  <div class="footer">
    <div class="contact">
      <p>
        ${ settings['author_name'] }
      </p>
    </div>
    <div class="contact">
      <p>
        <a href="${ settings['author_email'] }">${ settings['author_email'] }</a>
      </p>
    </div>
    <div class="rss">
      <a href="atom.xml"><img src="img/rss.png" alt="Subscribe to RSS Feed" /></a>
    </div>
  </div>
</div>
</body>
</html>
