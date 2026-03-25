import base64
import time
import urllib.parse
import json
import os
from fastapi import FastAPI, Response, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from openai import OpenAI
import uvicorn

app = FastAPI()

CONFIG_FILE = "config.json"

# --- 1. 声音列表配置 ---
VOICES = {
    "mimo_default": "MiMo-默认",
    "default_zh": "MiMo-中文女声",
    "default_en": "MiMo-英文女声",
}


def load_config():
    default_config = {
        "api_key": "",
        "admin_password": "admin",
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return default_config


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# --- 2. Web UI 管理后台 ---
@app.get("/")
async def index_page(request: Request):
    config = load_config()
    base_url = str(request.base_url).replace("http://", "https://").rstrip("/")

    options_html = "".join(
        [f'<option value="{k}">{v}</option>' for k, v in VOICES.items()]
    )

    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>小米 TTS</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, sans-serif; background: #f5f5f5; min-height: 100vh; }}
            .header {{ background: #fff; padding: 15px 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }}
            .header h1 {{ font-size: 18px; color: #333; }}
            .header .settings {{ display: flex; gap: 10px; align-items: center; }}
            .header input {{ padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; width: 200px; }}
            .header button {{ padding: 6px 12px; background: #007bff; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }}
            .main {{ display: flex; gap: 15px; padding: 15px; height: calc(100vh - 60px); }}
            .panel {{ background: #fff; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .left {{ width: 250px; display: flex; flex-direction: column; gap: 15px; }}
            .center {{ flex: 1; display: flex; flex-direction: column; }}
            .right {{ width: 300px; overflow-y: auto; }}
            .section-title {{ font-size: 14px; font-weight: bold; color: #333; margin-bottom: 10px; }}
            label {{ font-size: 13px; color: #666; margin-bottom: 5px; display: block; }}
            select {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; }}
            textarea {{ width: 100%; flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; resize: none; }}
            .btn {{ width: 100%; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; margin-top: 8px; }}
            .btn-primary {{ background: #007bff; color: #fff; }}
            .btn-success {{ background: #28a745; color: #fff; }}
            .btn:hover {{ opacity: 0.9; }}
            .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
            .import-section {{ margin-top: 10px; }}
            .import-btn {{ display: flex; align-items: center; gap: 8px; padding: 10px; background: #f8f9fa; border: 1px solid #ddd; border-radius: 6px; cursor: pointer; margin-top: 8px; font-size: 13px; }}
            .import-btn:hover {{ background: #e9ecef; }}
            .history-item {{ background: #f8f9fa; border-radius: 6px; padding: 10px; margin-bottom: 10px; }}
            .history-text {{ font-size: 12px; color: #666; margin-bottom: 8px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
            .history-audio {{ width: 100%; height: 32px; }}
            .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center; }}
            .modal.show {{ display: flex; }}
            .modal-content {{ background: #fff; padding: 20px; border-radius: 8px; width: 350px; text-align: center; }}
            .modal-content h3 {{ margin-bottom: 15px; }}
            .modal-content input {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px; }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
    </head>
    <body>
        <div class="header">
            <h1>🔊 小米 TTS</h1>
            <div class="settings">
                <span style="font-size:13px; color:#666;">API Key</span>
                <input type="password" id="api_key" placeholder="sk-..." value="{config["api_key"]}">
                <span style="font-size:13px; color:#666;">访问 Token</span>
                <input type="text" id="admin_password" placeholder="防盗刷密码" value="{config["admin_password"]}">
                <button onclick="saveConfig()">保存</button>
            </div>
        </div>
        <div class="main">
            <div class="left">
                <div class="panel">
                    <div class="section-title">发音人</div>
                    <label>选择音色</label>
                    <select id="voice_select">{options_html}</select>
                    <label style="margin-top:12px">风格</label>
                    <select id="style_preset" onchange="applyStyle()">
                        <option value="">无风格</option>
                        <option value="变快">变快</option>
                        <option value="变慢">变慢</option>
                        <option value="开心">开心</option>
                        <option value="悲伤">悲伤</option>
                        <option value="生气">生气</option>
                        <option value="悄悄话">悄悄话</option>
                        <option value="夹子音">夹子音</option>
                        <option value="台湾腔">台湾腔</option>
                        <option value="东北话">东北话</option>
                        <option value="四川话">四川话</option>
                        <option value="河南话">河南话</option>
                        <option value="粤语">粤语</option>
                        <option value="唱歌">唱歌</option>
                        <option value="custom">自定义...</option>
                    </select>
                    <input type="text" id="style_custom" placeholder="输入风格，如：孙悟空" style="display:none; margin-top:8px; padding:8px; border:1px solid #ddd; border-radius:6px; font-size:13px;">
                    <button class="btn btn-primary" onclick="generate()" id="gen_btn">🎧 试听</button>
                </div>
                <div class="panel import-section">
                    <div class="section-title">导入阅读 App</div>
                    <div class="import-btn" onclick="directImport()">📱 直接导入</div>
                    <div class="import-btn" onclick="showQRModal()">📷 扫码导入</div>
                </div>
            </div>
            <div class="center">
                <div class="panel" style="flex:1; display:flex; flex-direction:column;">
                    <div class="section-title">输入文本</div>
                    <textarea id="text_input" placeholder="请输入要转换的文本...">君不见黄河之水天上来，奔流到海不复回。</textarea>
                </div>
            </div>
            <div class="right">
                <div class="panel" style="height:100%;">
                    <div class="section-title">试听记录</div>
                    <div id="history_list"></div>
                </div>
            </div>
        </div>

        <div class="modal" id="qr_modal">
            <div class="modal-content">
                <h3>扫码导入</h3>
                <p style="font-size:13px; color:#666; margin-bottom:15px;">用阅读 App 扫描下方二维码</p>
                <div id="qr_code" style="display:flex; justify-content:center; padding:10px;"></div>
                <button class="btn btn-primary" style="margin-top:15px;" onclick="closeQRModal()">关闭</button>
            </div>
        </div>

        <script>
            const baseUrl = "{base_url}";
            let historyList = [];

            function saveConfig() {{
                const apiKey = document.getElementById('api_key').value;
                const token = document.getElementById('admin_password').value;
                fetch('/save', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                    body: `api_key=${{encodeURIComponent(apiKey)}}&admin_password=${{encodeURIComponent(token)}}`
                }}).then(() => alert('已保存'));
            }}

            function applyStyle() {{
                const preset = document.getElementById('style_preset').value;
                const custom = document.getElementById('style_custom');
                custom.style.display = preset === 'custom' ? 'block' : 'none';
            }}

            function generate() {{
                const token = document.getElementById('admin_password').value;
                const text = document.getElementById('text_input').value.trim();
                const voice = document.getElementById('voice_select').value;
                const btn = document.getElementById('gen_btn');
                
                let style = document.getElementById('style_preset').value;
                if (style === 'custom') {{
                    style = document.getElementById('style_custom').value.trim();
                }}
                
                const finalText = style ? `<style>${{style}}</style>${{text}}` : text;
                
                if (!token) return alert('请先填写 Token');
                if (!text) return alert('请输入文本');
                
                btn.innerHTML = '⏳ 生成中...';
                btn.disabled = true;
                
                const url = `/tts?token=${{encodeURIComponent(token)}}&voice=${{encodeURIComponent(voice)}}&text=${{encodeURIComponent(finalText)}}`;
                
                const item = {{ text: style ? `[${{style}}] ${{text}}` : text, voice: voice, url: url, time: new Date().toLocaleTimeString() }};
                historyList.unshift(item);
                renderHistory();
                
                const audio = new Audio(url);
                audio.oncanplay = () => {{ btn.innerHTML = '🎧 试听'; btn.disabled = false; audio.play(); }};
                audio.onerror = () => {{ btn.innerHTML = '🎧 试听'; btn.disabled = false; alert('生成失败'); }};
            }}

            function renderHistory() {{
                const container = document.getElementById('history_list');
                container.innerHTML = historyList.map((item, i) => `
                    <div class="history-item">
                        <div class="history-text">${{item.text}}</div>
                        <audio class="history-audio" controls preload="none" src="${{item.url}}"></audio>
                    </div>
                `).join('');
            }}

            function directImport() {{
                const token = document.getElementById('admin_password').value;
                const voice = document.getElementById('voice_select').value;
                const apiUrl = `${{baseUrl}}/api/legado-import?token=${{encodeURIComponent(token)}}&voice=${{voice}}`;
                const importUrl = `legado://import/httpTTS?src=${{encodeURIComponent(apiUrl)}}`;
                window.location.href = importUrl;
            }}

            function showQRModal() {{
                const token = document.getElementById('admin_password').value;
                const voice = document.getElementById('voice_select').value;
                const url = `${{baseUrl}}/api/legado-import?token=${{encodeURIComponent(token)}}&voice=${{voice}}`;
                
                const qrContainer = document.getElementById('qr_code');
                qrContainer.innerHTML = '';
                new QRCode(qrContainer, {{
                    text: url,
                    width: 200,
                    height: 200,
                    colorDark: '#000000',
                    colorLight: '#ffffff',
                }});
                document.getElementById('qr_modal').classList.add('show');
            }}
            function closeQRModal() {{
                document.getElementById('qr_modal').classList.remove('show');
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/save")
async def save_settings(
    admin_password: str = Form(...),
    api_key: str = Form(...),
):
    save_config(
        {
            "admin_password": admin_password,
            "api_key": api_key,
        }
    )
    return RedirectResponse(url="/", status_code=303)


# --- 3. 核心功能：朗读接口 (严格校验 URL 里的 Token 防盗刷) ---
def verify_access(request: Request, config: dict):
    # 彻底放弃 Header 鉴权，只验证 URL 里的 token，规避安卓播放器吞 Header 的 Bug
    token_query = request.query_params.get("token", "")
    return token_query == config["admin_password"]


@app.get("/tts")
def tts_forwarder(request: Request):
    config = load_config()
    if not verify_access(request, config):
        print(f"[{time.strftime('%H:%M:%S')}] ❌ 拦截：播放器未携带合法 Token")
        return Response(status_code=403, content="Forbidden: Token 错误")

    text = request.query_params.get("text", "")
    voice = request.query_params.get("voice", "mimo_default")
    text = urllib.parse.unquote(urllib.parse.unquote(text))

    if not text:
        return Response(status_code=400, content="Empty text")

    try:
        client = OpenAI(
            api_key=config["api_key"], base_url="https://api.xiaomimimo.com/v1"
        )
        response = client.chat.completions.create(
            model="mimo-v2-tts",
            messages=[
                {"role": "user", "content": "请朗读"},
                {"role": "assistant", "content": text},
            ],
            audio={"format": "mp3", "voice": voice},
            stream=False,
        )
        audio_data = response.choices[0].message.audio
        audio_b64 = (
            audio_data.get("data")
            if isinstance(audio_data, dict)
            else getattr(audio_data, "data", None)
        )

        if not audio_b64:
            return Response(status_code=500, content="API Error")

        audio_bytes = base64.b64decode(audio_b64)

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Length": str(len(audio_bytes)),
                "Cache-Control": "max-age=3600",
                "Connection": "keep-alive",
            },
        )
    except Exception as e:
        return Response(status_code=500, content=str(e))


# --- 4. 导入接口：完美拼装你在上文指定的格式 ---
@app.get("/api/legado-import")
async def legado_import(request: Request, voice: str = "mimo_default"):
    config = load_config()

    # 验证导入请求，防止别人乱刷配置
    if request.query_params.get("token") != config["admin_password"]:
        return Response(status_code=403, content="Forbidden: 导入 Token 错误")

    base_url = str(request.base_url).replace("http://", "https://").rstrip("/")
    v_name = VOICES.get(voice, f"音色({voice})")

    # ★ 完美对齐：直接在你指定的基础 URL 里，把 token 无缝安插在 text 前面
    safe_token = urllib.parse.quote(config["admin_password"])
    tts_url = f"{base_url}/tts?voice={voice}&volume=100&pitch=0&personality=undefined&rate={{{{(speakSpeed - 10) * 2}}}}&token={safe_token}&text={{{{java.encodeURI(speakText)}}}}"

    config_data = {
        "name": f"小米 - {v_name}",
        "url": tts_url,
        "contentType": "audio/mpeg",
        "id": int(time.time() * 1000),
        "concurrentRate": "",
        "loginUrl": "",
        "loginUi": "",
        "loginCheckJs": "",
        # 严格保留官方格式装样子的 undefined 请求头
        "header": '{"Authorization":"Bearer undefined"}',
    }

    return JSONResponse(content=[config_data])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8099)
