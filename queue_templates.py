"""Phase 4 — Review queue HTML templates (list + detail views)."""

QUEUE_LIST_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Review queue · PocketPlot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600&family=Karla:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
body{font-family:Karla;background:#f6f0e1;color:#1a241d;margin:0;padding:0}
.wrap{max-width:1100px;margin:0 auto;padding:32px 24px}
h1{font-family:Fraunces;font-weight:600;font-size:28px;margin:0 0 16px;color:#1a241d}
.tabs{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
.tab{font-family:Karla;font-size:13px;font-weight:600;padding:7px 14px;border-radius:99px;text-decoration:none;background:#fff;color:#5c7c5a;border:1px solid #d8cfb3}
.tab.active{background:#5c7c5a;color:#fff;border-color:#5c7c5a}
.tab .count{font-size:11px;font-weight:400;margin-left:6px;opacity:.8}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #d8cfb3}
th{padding:10px 14px;text-align:left;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#5c7c5a;background:#ecdfc3;font-family:Karla;font-weight:600}
td{padding:12px 14px;border-top:1px solid #ecdfc3;font-family:Georgia,serif;color:#1a241d;vertical-align:top}
.title{font-weight:600;color:#1a241d}
.title a{color:#c46a3f;text-decoration:none}
.title a:hover{text-decoration:underline}
.meta{font-size:12px;color:#7a8a6a;margin-top:4px;font-family:Karla}
.word{font-style:italic;color:#c46a3f;font-size:14px}
.empty{padding:40px;text-align:center;color:#7a8a6a;font-style:italic}
.actions{font-family:Karla;font-size:12px}
.actions a{color:#5c7c5a;text-decoration:none;margin-right:8px}
.actions a:hover{text-decoration:underline}
.badge{display:inline-block;font-size:10px;letter-spacing:.1em;text-transform:uppercase;padding:2px 6px;border-radius:4px;background:#ecdfc3;color:#5c7c5a;font-family:Karla;font-weight:600}
.badge.pro{background:#c9a96e;color:#fff}
.bulkbar{margin-bottom:14px;font-family:Karla;font-size:13px}
.bulkbar button{background:#c46a3f;color:#fff;border:none;padding:8px 16px;border-radius:99px;font-weight:700;font-family:Karla;cursor:pointer;font-size:13px}
.bulkbar button:hover{background:#a8572f}
.back{display:inline-block;margin-bottom:14px;color:#5c7c5a;text-decoration:none;font-family:Karla;font-size:13px}
.back:hover{text-decoration:underline}
</style></head><body>
<div class="wrap">
  <a class="back" href="/admin/dashboard">&larr; Back to dashboard</a>
  <h1>Review queue</h1>
  <div class="tabs">
    <a class="tab {{'active' if status=='pending' else ''}}" href="/admin/queue?status=pending">Pending <span class="count">{{counts.pending}}</span></a>
    <a class="tab {{'active' if status=='approved' else ''}}" href="/admin/queue?status=approved">Approved <span class="count">{{counts.approved}}</span></a>
    <a class="tab {{'active' if status=='rejected' else ''}}" href="/admin/queue?status=rejected">Rejected <span class="count">{{counts.rejected}}</span></a>
    <a class="tab {{'active' if status=='sent' else ''}}" href="/admin/queue?status=sent">Sent <span class="count">{{counts.sent}}</span></a>
    <a class="tab {{'active' if status=='all' else ''}}" href="/admin/queue?status=all">All <span class="count">{{counts.total}}</span></a>
  </div>
  {% if rows %}
  <form method="POST" action="/admin/queue/bulk-approve" id="bulk-form" class="bulkbar">
    <label><input type="checkbox" id="select-all"> Select all</label>
    <button type="submit">Bulk-approve &amp; send</button>
  </form>
  <table>
    <thead><tr><th style="width:30px;"></th><th>Title</th><th>Word</th><th>For</th><th>Queued</th><th>Status / Actions</th></tr></thead>
    <tbody>
    {% for r in rows %}
      <tr>
        <td><input type="checkbox" name="qid" value="{{r.id}}" form="bulk-form" class="row-check"></td>
        <td><div class="title"><a href="/admin/queue/{{r.id}}">{{r.story_obj.title or '(untitled)'}}</a></div>
            <div class="meta">{{r.email}}{% if r.plan=='pro' %} <span class="badge pro">PRO</span>{% endif %}</div>
        </td>
        <td><span class="word">{{r.word_obj.w or '—'}}</span></td>
        <td>{{r.child_name}}</td>
        <td>{{r.created_at[:10]}}</td>
        <td class="actions">
          {{r.status}}
          <a href="/admin/queue/{{r.id}}">view</a>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <script>
    document.getElementById('select-all').addEventListener('change', function(e) {
      document.querySelectorAll('.row-check').forEach(function(cb){ cb.checked = e.target.checked; });
    });
  </script>
  {% else %}
  <div class="empty">No items match this filter. Generate stories via /admin/run to populate the queue.</div>
  {% endif %}
</div>
</body></html>"""


QUEUE_DETAIL_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{{row.story_obj.title}} · Review · PocketPlot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600&family=Karla:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
body{font-family:Karla;background:#f6f0e1;color:#1a241d;margin:0;padding:0}
.wrap{max-width:760px;margin:0 auto;padding:32px 24px}
.back{display:inline-block;margin-bottom:14px;color:#5c7c5a;text-decoration:none;font-family:Karla;font-size:13px}
.back:hover{text-decoration:underline}
h1{font-family:Fraunces;font-weight:600;font-size:30px;margin:0 0 8px;color:#1a241d;line-height:1.2}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#5c7c5a;margin-bottom:16px}
.meta{font-family:Karla;font-size:13px;color:#7a8a6a;margin-bottom:18px;background:#fff;padding:10px 14px;border-radius:8px;border:1px solid #ecdfc3}
.meta b{color:#1a241d}
.hero{background:#fff;border:1px solid #d8cfb3;border-radius:12px;padding:18px;text-align:center;margin:18px 0}
.hero svg{max-width:100%;height:auto;display:block;border-radius:8px;margin:0 auto}
.story{background:#fff;border:1px solid #d8cfb3;border-radius:12px;padding:24px;margin-bottom:18px;font-family:Georgia,serif;line-height:1.7}
.story p{margin:0 0 14px}
.learning{background:#fdf3dc;border:1px solid #e0c98c;border-radius:10px;padding:16px 18px;margin-bottom:14px}
.learning h3{font-family:Fraunces;font-size:14px;color:#5c7c5a;margin:0 0 6px;letter-spacing:.04em}
.learning .word{font-style:italic;color:#c46a3f;font-family:Fraunces;font-size:22px;margin:0 0 6px}
.questions li{margin:6px 0;font-family:Georgia,serif}
.actions{position:sticky;bottom:20px;background:#fff;border:1px solid #d8cfb3;border-radius:99px;padding:8px 14px;display:flex;gap:10px;justify-content:center;box-shadow:0 8px 24px rgba(60,40,20,.18);margin-top:24px;flex-wrap:wrap}
.actions button,.actions a{border:none;padding:10px 20px;border-radius:99px;font-weight:700;font-family:Karla;font-size:13px;cursor:pointer;text-decoration:none;display:inline-block}
.actions .approve{background:#5c7c5a;color:#fff}
.actions .reject{background:#e88960;color:#fff}
.actions .approve:hover{background:#4a6648}
.actions .reject:hover{background:#c46a3f}
.actions .secondary{background:#ecdfc3;color:#5c7c5a}
.actions .approve-form,.actions .reject-form{display:contents}
.note{width:100%;border:1px solid #d8cfb3;border-radius:8px;padding:8px;font-family:Karla;font-size:13px;box-sizing:border-box;margin-top:12px;resize:vertical;min-height:48px}
</style></head><body>
<div class="wrap">
  <a class="back" href="/admin/queue">&larr; Back to queue</a>
  <div class="eyebrow">Review queue · #{{row.id}} · status: {{row.status}}</div>
  <h1>{{row.story_obj.title or '(untitled)'}}</h1>
  <div class="meta">
    <b>{{row.child_name}}</b> ({{row.email}}) · age {{row.child_age}}
    {% if row.plan=='pro' %} · <span style="color:#c9a96e;font-weight:700;">PRO{%if row.pro_tier%} {{row.pro_tier|upper}}{%endif%}</span>{% endif %}
    &nbsp;·&nbsp; queued {{row.created_at[:16]}} · seed {{row.seed}}
  </div>
  {% if row.hero_svg %}
  <div class="hero">{{row.hero_svg|safe}}</div>
  {% endif %}
  <div class="story">
    {% set paragraphs = (row.story_obj.body or '').split('\\n\\n') %}
    {% for para in paragraphs if para.strip() %}
      <p>{{para}}</p>
    {% endfor %}
  </div>
  {% if row.word_obj and row.word_obj.w %}
  <div class="learning">
    <h3>Word of the day</h3>
    <div class="word">{{row.word_obj.w}}</div>
    <div>{{row.word_obj.d}}</div>
  </div>
  {% endif %}
  {% if row.questions_list %}
  <div class="learning">
    <h3>Story talk</h3>
    <ol class="questions">
      {% for q in row.questions_list %}
        <li>{{q.q if q.q is defined else q}}</li>
      {% endfor %}
    </ol>
  </div>
  {% endif %}
  {% if row.parent_guide %}
  <div class="learning">
    <h3>Parent guide (Pro)</h3>
    <div>{{row.parent_guide}}</div>
  </div>
  {% endif %}
  {% if row.moment_text %}
  <div class="learning">
    <h3>Moment of the day</h3>
    <div>{{row.moment_text}}</div>
  </div>
  {% endif %}
  {% if row.status == 'pending' %}
  <div class="actions">
    <form method="POST" action="/admin/queue/{{row.id}}/approve" class="approve-form">
      <input type="text" name="note" class="note" placeholder="Optional reviewer note (saved with the approval)..." style="flex:1;min-width:240px;">
      <button type="submit" class="approve">Approve &amp; Send</button>
    </form>
  </div>
  <div class="actions">
    <form method="POST" action="/admin/queue/{{row.id}}/reject" class="reject-form">
      <input type="text" name="note" class="note" placeholder="Optional rejection note..." style="flex:1;min-width:240px;">
      <button type="submit" class="reject">Reject</button>
      <a href="/admin/queue" class="secondary">Cancel</a>
    </form>
  </div>
  {% else %}
  <div class="actions">
    <span style="align-self:center;font-family:Karla;font-size:13px;color:#7a8a6a;font-style:italic;">This item is {{row.status}}{%if row.reviewed_at%} (reviewed {{row.reviewed_at[:16]}}){%endif%}.</span>
    <a href="/admin/queue" class="secondary">Back to queue</a>
  </div>
  {% endif %}
</div>
</body></html>"""
