from flask import Flask, render_template, request, send_file, flash, jsonify
import os
import uuid
import yt_dlp
import re
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_' + str(uuid.uuid4())
app.config['DOWNLOAD_FOLDER'] = os.path.join(os.getcwd(), 'downloads')

download_progress = {
    'percentage': 0,
    'status': 'idle',
    'filename': ''
}

def get_video_info(url):
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Sin título')
            clean_title = re.sub(r'[\\/*?:"<>|]', '', title)
            
            return {
                'titulo': clean_title,
                'duracion': info.get('duration', 0),
                'canal': info.get('uploader', 'Desconocido'),
                'thumbnail': info.get('thumbnail', ''),
                'formats': info.get('formats', [])
            }
    except Exception as e:
        print(f"Error al obtener info: {e}")    
        return None

def my_hook(d):
    global download_progress
    if d['status'] == 'downloading':
        download_progress['percentage'] = d['_percent_str']
        download_progress['status'] = 'downloading'
    elif d['status'] == 'finished':
        download_progress['status'] = 'finished'
        download_progress['filename'] = d['filename']

def descargar_media(url, formato, calidad='720'):
    global download_progress
    try:
        video_info = get_video_info(url)
        if not video_info:
            raise Exception("No se pudo obtener información del video")
        
        safe_title = re.sub(r'[\\/*?:"<>|]', '', video_info['titulo'])
        nombre_base = os.path.join(app.config['DOWNLOAD_FOLDER'], safe_title[:50])
        ruta_temp = nombre_base
        
        opts = {
            'outtmpl': ruta_temp,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [my_hook],
        }

        if formato == 'mp3':
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'extract_audio': True
            })
            ext_final = '.mp3'
        else:
            opts.update({
                'format': f'bestvideo[height<={calidad}]+bestaudio/best',
                'merge_output_format': 'mp4'
            })
            ext_final = '.mp4'

        download_progress = {
            'percentage': '0%',
            'status': 'starting',
            'filename': ''
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
            archivo_final = f"{ruta_temp}{ext_final}"
            
            if not os.path.exists(archivo_final):
                nombre_base = os.path.join(app.config['DOWNLOAD_FOLDER'], str(uuid.uuid4()))
                opts['outtmpl'] = nombre_base
                ydl.download([url])
                archivo_final = f"{nombre_base}{ext_final}"
                
            return archivo_final

    except Exception as e:
        if 'ruta_temp' in locals():
            for ext in ['.mp4', '.mp3', '.webm', '.m4a']:
                if os.path.exists(f"{ruta_temp}{ext}"):
                    os.remove(f"{ruta_temp}{ext}")
        raise Exception(f"Error al procesar el video: {str(e)}")

@app.route('/progress')
def progress():
    global download_progress
    return jsonify(download_progress)

@app.route('/', methods=['GET', 'POST'])
def index():
    global download_progress
    video_info = None
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        
        if 'analizar' in request.form:
            if url and any(d in url for d in ['youtube.com', 'youtu.be']):
                video_info = get_video_info(url)
                if not video_info:
                    flash('❌ No se pudo obtener información del video', 'error')
            
        elif 'descargar' in request.form:
            formato = request.form.get('formato')
            calidad = request.form.get('calidad', '720')
            try:
                archivo = descargar_media(url, formato, calidad)
                nombre_descarga = os.path.basename(archivo)
                
                response = send_file(
                    archivo,
                    as_attachment=True,
                    download_name=nombre_descarga
                )
                
                @response.call_on_close
                def clean_up():
                    try:
                        os.remove(archivo)
                    except:
                        pass
                        
                return response
                
            except Exception as e:
                flash(f'❌ Error: {str(e)}', 'error')
                download_progress = {
                    'percentage': 0,
                    'status': 'error',
                    'filename': ''
                }
    
    download_progress = {
        'percentage': 0,
        'status': 'idle',
        'filename': ''
    }
    return render_template('index.html', video_info=video_info)

if __name__ == '__main__':
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)