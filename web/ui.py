"""Minimal browser UI for the ResearchGraph API."""

from __future__ import annotations

from typing import Any, Callable

from web.api import ApiApplication


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>ResearchGraph</title>
<style>body{font:16px system-ui;max-width:900px;margin:40px auto;padding:0 20px}label{display:block;margin-top:12px}input,textarea{width:100%;padding:8px}button{margin-top:16px;padding:8px 14px}pre{white-space:pre-wrap;background:#f4f4f4;padding:16px}</style>
</head><body><h1>ResearchGraph</h1>
<p>最小研究流程演示：创建项目、生成并确认子问题，然后运行离线研究流程。</p>
<form id="project"><label>项目标题<input name="title" required value="学习效果研究"></label>
<label>研究问题<textarea name="research_question" required>大语言模型是否能够提升中学生的学习效果？</textarea></label>
<label>研究对象<input name="subject" value="中学生"></label>
<label>关注重点<input name="focus" value="数学和英语学习"></label>
<button>创建项目</button></form>
<section id="workflow" hidden><h2>子问题</h2><pre id="questions"></pre><button id="run">确认并运行研究</button></section>
<h2>报告</h2><pre id="report">尚未生成报告。</pre>
<script>
const form=document.querySelector('#project'), workflow=document.querySelector('#workflow');
let projectId;
async function api(url, options={}) { const response=await fetch(url, options); const data=await response.json(); if(!response.ok) throw Error(data.error||'请求失败'); return data; }
form.onsubmit=async event=>{event.preventDefault(); try { const data=Object.fromEntries(new FormData(form)); const created=await api('/api/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); projectId=created.project.id; const questions=await api(`/api/projects/${projectId}/questions`,{method:'POST'}); document.querySelector('#questions').textContent=JSON.stringify(questions,null,2); workflow.hidden=false; } catch(error){alert(error.message)} };
document.querySelector('#run').onclick=async()=>{try { await api(`/api/projects/${projectId}/questions/confirm`,{method:'POST'}); const result=await api(`/api/projects/${projectId}/run`,{method:'POST'}); document.querySelector('#report').textContent=result.report.content; } catch(error){alert(error.message)} };
</script></body></html>"""


class WebApplication:
    """Serve the single-page UI and delegate API paths to ApiApplication."""

    def __init__(self, api: ApiApplication):
        self.api = api

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]):
        if environ.get("PATH_INFO", "/") == "/" and environ.get("REQUEST_METHOD", "GET") == "GET":
            body = INDEX_HTML.encode("utf-8")
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"),
                                       ("Content-Length", str(len(body)))])
            return [body]
        return self.api(environ, start_response)
