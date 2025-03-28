from flask import Flask, render_template, request, send_file, flash, jsonify
import os
import uuid
import yt_dlp
import re
import logging

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_' + str(uuid.uuid4())
app.config['DOWNLOAD_FOLDER'] = os.path.join(os.getcwd(), 'downloads')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

download_progress = {
    'percentage': 0,
    'status': 'idle',
    'filename': ''
}

def get_video_info(url, platform):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if platform == 'tiktok':
                return {
                    'titulo': info.get('title', 'Video de TikTok'),
                    'duracion': info.get('duration', 0),
                    'canal': info.get('uploader', 'Usuario de TikTok'),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': info.get('formats', []),
                    'platform': 'tiktok'
                }
            else:
                return {
                    'titulo': info.get('title', 'Sin título'),
                    'duracion': info.get('duration', 0),
                    'canal': info.get('uploader', 'Desconocido'),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': info.get('formats', []),
                    'platform': 'youtube'
                }
                
    except Exception as e:
        logger.error(f"Error al obtener info: {e}")
        return None

def my_hook(d):
    global download_progress
    if d['status'] == 'downloading':
        download_progress['percentage'] = d['_percent_str']
        download_progress['status'] = 'downloading'
    elif d['status'] == 'finished':
        download_progress['status'] = 'finished'
        download_progress['filename'] = d['filename']

def descargar_media(url, formato, calidad='720', platform='youtube'):
    global download_progress
    try:
        if platform == 'tiktok' and 'vt.tiktok.com' in url and not url.startswith('http'):
            url = 'https://' + url
            
        video_info = get_video_info(url, platform)
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

        if platform == 'tiktok':
            opts.update({
                'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b',
                'merge_output_format': 'mp4',
                'extractor_args': {
                    'tiktok': {
                        'format': 'download_addr',
                        'video_data': 'wm',
                    }
                },
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            })
            ext_final = '.mp4'
        elif formato == 'mp3':
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
            info = ydl.extract_info(url, download=True)
            archivo_final = ydl.prepare_filename(info)
            
            if not archivo_final.endswith(ext_final):
                if os.path.exists(archivo_final + ext_final):
                    archivo_final += ext_final
                elif os.path.exists(archivo_final):
                    pass
                else:
                    for f in os.listdir(app.config['DOWNLOAD_FOLDER']):
                        if f.startswith(os.path.basename(nombre_base)):
                            archivo_final = os.path.join(app.config['DOWNLOAD_FOLDER'], f)
                            break
            
            if not os.path.exists(archivo_final):
                raise Exception(f"El archivo descargado no se encontró: {archivo_final}")
                
            return archivo_final

    except Exception as e:
        if 'ruta_temp' in locals():
            for ext in ['.mp4', '.mp3', '.webm', '.m4a', '.mkv', '.part']:
                if os.path.exists(f"{ruta_temp}{ext}"):
                    os.remove(f"{ruta_temp}{ext}")
                if os.path.exists(ruta_temp):
                    os.remove(ruta_temp)
        logger.error(f"Error al descargar: {str(e)}")
        raise Exception(f"Error al procesar el video: {str(e)}")

@app.route('/progress')
def progress():
    global download_progress
    return jsonify(download_progress)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/youtube', methods=['GET', 'POST'])
def youtube():
    global download_progress
    video_info = None
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        
        if 'analizar' in request.form:
            if url and any(d in url for d in ['youtube.com', 'youtu.be']):
                video_info = get_video_info(url, 'youtube')
                if not video_info:
                    flash('❌ No se pudo obtener información del video', 'error')
            
        elif 'descargar' in request.form:
            formato = request.form.get('formato')
            calidad = request.form.get('calidad', '720')
            try:
                archivo = descargar_media(url, formato, calidad, 'youtube')
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
    return render_template('youtube.html', video_info=video_info)

@app.route('/tiktok', methods=['GET', 'POST'])
def tiktok():
    global download_progress
    video_info = None
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        
        if 'analizar' in request.form:
            if url and ('tiktok.com' in url or 'vt.tiktok.com' in url):
                try:
                    if 'vt.tiktok.com' in url and not url.startswith('http'):
                        url = 'https://' + url
                    
                    video_info = get_video_info(url, 'tiktok')
                    if not video_info:
                        flash('❌ No se pudo obtener información del video', 'error')
                except Exception as e:
                    logger.error(f"Error al procesar URL de TikTok: {str(e)}")
                    flash('❌ URL de TikTok no válida o video no disponible', 'error')
            
        elif 'descargar' in request.form:
            try:
                url = request.form.get('url', '').strip()
                if 'vt.tiktok.com' in url and not url.startswith('http'):
                    url = 'https://' + url
                
                archivo = descargar_media(url, 'mp4', '720', 'tiktok')
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
    return render_template('tiktok.html', video_info=video_info)

if __name__ == '__main__':
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)