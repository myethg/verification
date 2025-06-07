import discord
from discord.ext import commands
from flask import Flask, request, redirect, render_template_string
import requests
import asyncio
import threading
from urllib.parse import urlencode

app = Flask(__name__)
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET') 
REDIRECT_URI = os.getenv('REDIRECT_URI')
BOT_TOKEN = os.getenv('BOT_TOKEN')
VERIFICATION_CHANNEL_ID = int(os.getenv('VERIFICATION_CHANNEL_ID'))
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

@app.route('/')
def home():
    auth_params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': 'guilds identify'
    }
    
    auth_url = f"https://discord.com/oauth2/authorize?{urlencode(auth_params)}"
    
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Discord Verification</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                }
                
                .container {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 40px;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    max-width: 400px;
                    width: 90%;
                }
                
                .discord-logo {
                    width: 80px;
                    height: 80px;
                    background: #5865F2;
                    border-radius: 50%;
                    margin: 0 auto 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 40px;
                    font-weight: bold;
                }
                
                h1 {
                    font-size: 28px;
                    margin-bottom: 10px;
                    font-weight: 600;
                }
                
                .subtitle {
                    font-size: 16px;
                    opacity: 0.9;
                    margin-bottom: 30px;
                    line-height: 1.5;
                }
                
                .auth-btn {
                    background: #5865F2;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                    display: inline-block;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 15px rgba(88, 101, 242, 0.4);
                }
                
                .auth-btn:hover {
                    background: #4752C4;
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(88, 101, 242, 0.6);
                }
                
                .features {
                    margin-top: 30px;
                    text-align: left;
                }
                
                .feature {
                    display: flex;
                    align-items: center;
                    margin-bottom: 10px;
                    font-size: 14px;
                    opacity: 0.8;
                }
                
                .feature-icon {
                    margin-right: 10px;
                    font-size: 16px;
                }
                
                .security-note {
                    margin-top: 25px;
                    font-size: 12px;
                    opacity: 0.7;
                    padding: 15px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    border-left: 3px solid #5865F2;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="discord-logo">D</div>
                <h1>Account Verification</h1>
                <p class="subtitle">Verify your Discord account to prove you're not using an alt account</p>
                
                <a href="{{ auth_url }}" class="auth-btn">🔗 Connect Discord Account</a>
                
                <div class="features">
                    <div class="feature">
                        <span class="feature-icon">🔍</span>
                        <span>Server membership analysis</span>
                    </div>
                    <div class="feature">
                        <span class="feature-icon">📊</span>
                        <span>Account age verification</span>
                    </div>
                    <div class="feature">
                        <span class="feature-icon">🌍</span>
                        <span>Location & connection check</span>
                    </div>
                    <div class="feature">
                        <span class="feature-icon">⚡</span>
                        <span>Instant verification results</span>
                    </div>
                </div>
                
                <div class="security-note">
                    🔒 Your data is processed securely and only used for verification purposes
                </div>
            </div>
        </body>
        </html>
    ''', auth_url=auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in user_ip:
        user_ip = user_ip.split(',')[0].strip()
    
    if not code:
        return 'Authorization failed', 400

    try:
        token_data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        token_response = requests.post('https://discord.com/api/oauth2/token', data=token_data, headers=headers)
        token_json = token_response.json()
        
        access_token = token_json['access_token']
        
        auth_headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        user_response = requests.get('https://discord.com/api/users/@me', headers=auth_headers)
        guilds_response = requests.get('https://discord.com/api/users/@me/guilds', headers=auth_headers)
        
        user = user_response.json()
        guilds = guilds_response.json()
        
        ip_info = get_ip_info(user_ip)
        
        asyncio.run_coroutine_threadsafe(send_verification_data(user, guilds, user_ip, ip_info), bot.loop)
        
        return render_template_string('''
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>Verification Complete</h1>
                    <p>Your server data has been sent for verification. You may close this window.</p>
                </body>
            </html>
        ''')
        
    except Exception as e:
        print(f'Error during OAuth: {e}')
        return 'Verification failed', 500

def get_ip_info(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,org,as,proxy,hosting')
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

async def send_verification_data(user, guilds, user_ip, ip_info):
    channel = bot.get_channel(VERIFICATION_CHANNEL_ID)
    
    if not channel:
        print('Verification channel not found')
        return
    
    risk_level = 'Low'
    if len(guilds) < 5:
        risk_level = 'High'
    elif len(guilds) < 15:
        risk_level = 'Medium'
    
    risk_colors = {'Low': 0x00ff00, 'Medium': 0xffff00, 'High': 0xff0000}
    
    embed = discord.Embed(
        title='Member Verification',
        color=risk_colors[risk_level]
    )
    
    if user.get('avatar'):
        avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png"
        embed.set_thumbnail(url=avatar_url)
    
    embed.add_field(name='User', value=f"{user['username']}#{user['discriminator']}", inline=False)
    embed.add_field(name='User ID', value=user['id'], inline=False)
    embed.add_field(name='Account Created', value=f"<t:{int(((int(user['id']) >> 22) + 1420070400000) / 1000)}:F>", inline=False)
    embed.add_field(name='IP Address', value=user_ip, inline=False)
    
    if ip_info and ip_info.get('status') == 'success':
        location = f"{ip_info.get('city', 'Unknown')}, {ip_info.get('regionName', 'Unknown')}, {ip_info.get('country', 'Unknown')}"
        embed.add_field(name='Location', value=location, inline=False)
        embed.add_field(name='ISP', value=ip_info.get('isp', 'Unknown'), inline=False)
        
        proxy_detected = ip_info.get('proxy', False) or ip_info.get('hosting', False)
        vpn_status = "🔴 VPN/Proxy Detected" if proxy_detected else "🟢 Direct Connection"
        embed.add_field(name='Connection Type', value=vpn_status, inline=False)
        
        if proxy_detected and risk_level == 'Low':
            risk_level = 'Medium'
            embed.color = 0xffff00
    
    embed.add_field(name='Total Servers', value=str(len(guilds)), inline=False)
    embed.add_field(name='Alt Risk Level', value=risk_level, inline=False)
    
    mutual_servers = []
    for guild in bot.guilds:
        if any(g['id'] == str(guild.id) for g in guilds):
            mutual_servers.append(guild.name)
    
    if mutual_servers:
        embed.add_field(name='Mutual Servers', value='\n'.join(mutual_servers), inline=False)
    
    await channel.send(embed=embed)
    
    if guilds:
        server_list = [f"{guild['name']} ({guild['id']})" for guild in guilds]
        
        current_message = ""
        for server in server_list:
            if len(current_message + server + '\n') > 1900:
                await channel.send(f"```{current_message}```")
                current_message = server + '\n'
            else:
                current_message += server + '\n'
        
        if current_message:
            await channel.send(f"```{current_message}```")
    else:
        await channel.send("```No servers found```")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

def run_bot():
    bot.run(BOT_TOKEN)

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    run_flask()
