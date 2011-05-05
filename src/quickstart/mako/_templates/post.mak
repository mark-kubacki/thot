<%inherit file="master.mak"/>
<div id="post">
    <h1>${ page['title'] }</h1>
    <p class="meta">${ page['date'] | n,datetimeformat("%B %d, %Y") }</p>
    ${ page['content'] }
</div>
