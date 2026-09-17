"""Minimal browser UI for the ResearchGraph API."""

from __future__ import annotations

from typing import Any, Callable

from web.api import ApiApplication


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>ResearchGraph</title>
<style>
:root{color-scheme:light}*{box-sizing:border-box}body{font:16px system-ui;max-width:1000px;margin:32px auto;padding:0 20px;color:#172033;background:#f7f9fc}h1{margin-bottom:4px}.panel{background:white;border:1px solid #dfe5ee;border-radius:12px;padding:20px;margin:18px 0;box-shadow:0 2px 8px #1720330d}label{display:block;margin-top:12px;font-weight:600}input,textarea{width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;font:inherit}textarea{min-height:90px;resize:vertical}button{margin:12px 8px 0 0;padding:9px 15px;border:0;border-radius:6px;background:#2563eb;color:white;cursor:pointer}button.secondary{background:#64748b}button.danger{background:#dc2626}.question{display:flex;gap:10px;align-items:flex-start;margin:10px 0;padding:12px;background:#f8fafc;border-radius:8px}.question textarea{min-height:60px;flex:1}.question small{color:#64748b;min-width:25px;padding-top:10px}.status{padding:10px;background:#eff6ff;color:#1d4ed8;border-radius:6px}.error{background:#fef2f2;color:#b91c1c}.markdown{background:#fff;line-height:1.55}.markdown h1,.markdown h2,.markdown h3{margin:0.7em 0 0.25em;line-height:1.25}.markdown h1{font-size:1.6em}.markdown h2{font-size:1.3em}.markdown h3{font-size:1.1em}.markdown a{color:#2563eb}.markdown blockquote{border-left:4px solid #93c5fd;padding-left:12px;color:#475569}.markdown code{background:#f1f5f9;padding:2px 4px}.citation{position:relative;display:inline-block;margin:0 2px}.citation>a{display:inline-block;padding:1px 5px;border-radius:10px;background:#dbeafe;color:#1d4ed8;font:600 13px ui-monospace,monospace;text-decoration:none}.citation-card{display:none;position:absolute;z-index:10;left:0;top:calc(100% + 8px);width:320px;padding:12px;border:1px solid #bfdbfe;border-radius:8px;background:white;box-shadow:0 8px 24px #17203326;color:#172033;font:14px system-ui;line-height:1.5}.citation:hover .citation-card,.citation:focus-within .citation-card{display:block}.citation-card:before{content:"";position:absolute;top:-7px;left:14px;width:12px;height:12px;background:white;border-left:1px solid #bfdbfe;border-top:1px solid #bfdbfe;transform:rotate(45deg)}.citation-card strong{display:block;margin-bottom:5px}.citation-card p{margin:5px 0}.citation-card .excerpt{color:#475569}.citation-card a{word-break:break-all}.hidden{display:none}#report{padding:20px}
</style>
</head><body><h1>ResearchGraph</h1>
<p>深度研究工作台：先完善子问题，再确认并运行可追溯研究流程。</p>
<form id="project" class="panel"><h2>1. 创建研究项目</h2><label>项目标题<input name="title" required value="学习效果研究"></label>
<label>研究问题<textarea name="research_question" required>大语言模型是否能够提升中学生的学习效果？</textarea></label>
<label>时间范围<input name="time_range" placeholder="例如：2020-至今"></label><label>地区<input name="region" placeholder="例如：中国、全球"></label>
<label>研究对象<input name="subject" value="中学生"></label><label>关注重点<input name="focus" value="数学和英语学习"></label>
<button>创建项目</button></form>
<section id="workflow" class="panel hidden"><h2>2. 编辑并确认子问题</h2><div id="status" class="status">正在等待项目。</div><div id="questions"></div><button id="add" class="secondary">+ 添加子问题</button><button id="run">确认并运行研究</button></section>
<section class="panel"><h2>3. 研究报告</h2><div id="report" class="markdown">尚未生成报告。</div></section>
<script>
const form=document.querySelector('#project'), workflow=document.querySelector('#workflow'), questionsBox=document.querySelector('#questions'), statusBox=document.querySelector('#status'), runButton=document.querySelector('#run'); let projectId, questions=[], evidenceById={};
async function api(url, options={}) { const response=await fetch(url, options); const data=await response.json(); if(!response.ok) throw Error(data.error||'请求失败'); return data; }
function setStatus(text,error=false){statusBox.textContent=text;statusBox.className='status'+(error?' error':'')}
function renderQuestions(){questionsBox.innerHTML=''; questions.forEach((q,i)=>{const row=document.createElement('div');row.className='question';row.innerHTML=`<small>${i+1}</small><textarea aria-label="子问题 ${i+1}"></textarea><button class="danger" type="button">删除</button>`;const input=row.querySelector('textarea');input.value=q.text;input.oninput=()=>q.text=input.value;row.querySelector('button').onclick=async()=>{try{if(q.id)await api(`/api/projects/${projectId}/questions/${q.id}`,{method:'DELETE'});questions.splice(i,1);renderQuestions()}catch(error){setStatus(error.message,true)}};questionsBox.appendChild(row)})}
form.onsubmit=async event=>{event.preventDefault();const submit=form.querySelector('button');submit.disabled=true;workflow.classList.remove('hidden');setStatus('正在创建项目。');try{const data=Object.fromEntries(new FormData(form));const created=await api('/api/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});projectId=created.project.id;setStatus('项目已创建，正在使用 LLM 生成子问题，请稍候。');await api(`/api/projects/${projectId}/questions`,{method:'POST'});const result=await api(`/api/projects/${projectId}/questions`);questions=result.questions;renderQuestions();setStatus('子问题已生成，可编辑、删除或新增。');}catch(error){setStatus('项目已创建，但生成子问题失败：'+error.message,true)}finally{submit.disabled=false}};
document.querySelector('#add').onclick=async()=>{try{const result=await api(`/api/projects/${projectId}/questions/add`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'',position:questions.length+1})});questions.push(result.question);renderQuestions();questionsBox.lastElementChild.querySelector('textarea').focus()}catch(error){setStatus(error.message,true)}};
runButton.onclick=async()=>{if(!questions.length||questions.some(q=>!q.text.trim())){setStatus('请至少保留一个非空子问题。',true);return}runButton.disabled=true;setStatus('正在确认问题、搜索来源、提取证据并生成报告，请稍候……');try{for(const [i,q] of questions.entries())await api(`/api/projects/${projectId}/questions/${q.id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:q.text,position:i+1})});await api(`/api/projects/${projectId}/questions/confirm`,{method:'POST'});const result=await api(`/api/projects/${projectId}/run`,{method:'POST'});const evidence=await api(`/api/projects/${projectId}/evidence`);evidenceById=Object.fromEntries(evidence.evidence.map(item=>[item.id,item]));document.querySelector('#report').innerHTML=markdown(result.report.content);setStatus('研究完成。');}catch(error){setStatus(error.message,true)}finally{runButton.disabled=false}};
function escapeHtml(value){return String(value??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function citation(id){const item=evidenceById[id];if(!item)return `<span class="citation"><a href="#evidence-${id}">[E${id}]</a><span class="citation-card"><strong>证据 E${id}</strong><p>暂无详细信息</p></span></span>`;const source=item.source||{};return `<span class="citation" id="evidence-${id}"><a href="${escapeHtml(source.url||'#')}" target="_blank" rel="noreferrer">[E${id}]</a><span class="citation-card"><strong>${escapeHtml(source.title||'未命名来源')}</strong><p class="excerpt">${escapeHtml(item.excerpt)}</p><p>定位：${escapeHtml(item.locator||'未提供')}<br>类型：${escapeHtml(item.evidence_type||'未分类')}　立场：${escapeHtml(item.stance||'未标注')}<br>强度：${escapeHtml(item.strength||'未标注')}</p>${item.uncertainty?`<p>不确定性：${escapeHtml(item.uncertainty)}</p>`:''}<a href="${escapeHtml(source.url||'#')}" target="_blank" rel="noreferrer">打开来源 ↗</a></span></span>`}
function markdown(text){return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\[E(\d+)\]/g,(match,id)=>citation(id)).replace(/^### (.*)$/gm,'<h3>$1</h3>').replace(/^## (.*)$/gm,'<h2>$1</h2>').replace(/^# (.*)$/gm,'<h1>$1</h1>').replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,'<a href="$2" target="_blank" rel="noreferrer">$1</a>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/^> (.*)$/gm,'<blockquote>$1</blockquote>').replace(/^- (.*)$/gm,'<div>• $1</div>').replace(/\n\n/g,'<br>')}
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
