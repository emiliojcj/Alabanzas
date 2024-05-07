from flask import Flask, render_template, request, redirect, url_for, make_response, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Agrega esta línea para importar CORS
import pdfkit
from unidecode import unidecode
import openpyxl

app = Flask(__name__, template_folder='C:\\Users\\ejcj2\\Desktop\\Aplicacion Alabanzas')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///songs.db'
app.config['LOGO_PATH'] = 'C:/Users/ejcj2/Desktop/Aplicacion Alabanzas/logo.png'
CORS(app)
db = SQLAlchemy(app)

print(app.url_map)

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    lyrics = db.Column(db.Text)
    note = db.Column(db.String(100))  # Campo para la nota de la canción
    classification = db.Column(db.String(50))  # Campo para la clasificación de la canción

with app.app_context():
    db.drop_all()  # Eliminar todas las tablas existentes
    db.create_all()  # Crear las tablas nuevamente


def load_songs_from_excel(excel_file):
    with app.app_context():  # Entrar en el contexto de la aplicación Flask
        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2, values_only=True):  # Comenzar desde la segunda fila
                title, lyrics, note, classification = row[:4]  # Suponiendo que la primera columna es el título, la segunda la letra, la tercera la nota y la cuarta la clasificación
                # Verificar si la canción ya existe en la base de datos
                existing_song = Song.query.filter_by(title=title).first()
                if existing_song is None:  # Si la canción no existe, añadirla a la base de datos
                    song = Song(title=title, lyrics=lyrics, note=note, classification=classification)
                    db.session.add(song)
            db.session.commit()
            print("Los datos se han cargado exitosamente desde el archivo Excel.")
        except Exception as e:
            print(f"Error al cargar los datos desde el archivo Excel: {e}")


# Ruta al archivo Excel
excel_file_path = 'C:\\Users\\ejcj2\\Desktop\\Aplicacion Alabanzas\\base.xlsx'

# Llamar a la función para cargar los datos desde el archivo Excel
load_songs_from_excel(excel_file_path)

@app.route('/')
def index():
    songs = Song.query.all()
    return render_template('buscador.html', songs=songs)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    classification = request.args.get('classification')
    if query:
        # Normalizar la consulta eliminando acentos y caracteres especiales
        query_normalized = unidecode(query).lower()
        # Obtener todas las canciones de la base de datos
        all_songs = Song.query.all()
        # Filtrar las canciones que coinciden con la consulta normalizada y, si se proporciona, con la clasificación
        if classification:  # Si se proporciona una clasificación
            songs = [song for song in all_songs if query_normalized in unidecode(song.title).lower() and song.classification.lower() == classification.lower()]
        else:  # Si no se proporciona una clasificación
            songs = [song for song in all_songs if query_normalized in unidecode(song.title).lower()]
        if not songs:
            return render_template('buscador.html', songs=[], query=query, no_results=True)
    else:
        if classification:  # Si solo se proporciona una clasificación sin consulta
            # Convertir la clasificación proporcionada a minúsculas
            classification_lower = classification.lower()
            # Filtrar las canciones por la clasificación proporcionada (insensible a mayúsculas y minúsculas)
            songs = [song for song in Song.query.all() if song.classification.lower() == classification_lower]
        else:  # Si no hay consulta ni clasificación
            songs = Song.query.all()
    return render_template('buscador.html', songs=songs, query=query, no_results=False)


@app.route('/reset_search')
def reset_search():
    return redirect(url_for('search'))

@app.route('/add_song', methods=['POST'])
def add_song():
    title = request.form['title']
    lyrics = request.form['lyrics'] 
    note = request.form.get('note', '')  # Obtener la nota del formulario
    classification = request.form.get('classification', '')  # Obtener la clasificación del formulario
    new_song = Song(title=title, lyrics=lyrics, note=note, classification=classification)  # Crear una nueva canción con la nota y la clasificación
    db.session.add(new_song)
    db.session.commit()
    return redirect(url_for('search'))

# Especifica la ruta al ejecutable de wkhtmltopdf
config = pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
print(config.wkhtmltopdf)

@app.route('/download/<int:song_id>')
def download(song_id):
    song = Song.query.get_or_404(song_id)
    # Dividir la letra en dos partes
    lines = song.lyrics.split('\n')
    mid_point = len(lines) // 2
    song.lyrics_lines_1 = lines[:mid_point]
    song.lyrics_lines_2 = lines[mid_point:]

    # Renderizar la plantilla descarga.html y pasar la aplicación Flask
    rendered_html = render_template('descarga.html', song=song, app=app)
    print(rendered_html)

    # Convertir el contenido HTML en un PDF utilizando pdfkit y la configuración de wkhtmltopdf
    pdf = pdfkit.from_string(rendered_html, False, configuration=config)

    # Configurar la respuesta para descargar el PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={song.title}.pdf'

    return response

@app.route('/lyrics/<int:song_id>')
def show_lyrics(song_id):
    song = Song.query.get_or_404(song_id)
    # Dividir la letra en dos partes
    lines = song.lyrics.split('\n')
    mid_point = len(lines) // 2
    song.lyrics_lines_1 = lines[:mid_point]
    song.lyrics_lines_2 = lines[mid_point:]
    print("Letras")
    print(song.lyrics_lines_1)
    print(song.lyrics_lines_2)
    print(song.classification)
    
    return render_template('letra.html', song=song)

@app.route('/edit/<int:song_id>', methods=['GET', 'POST'])
def edit_lyrics(song_id):
    song = Song.query.get_or_404(song_id)
    if request.method == 'POST':
        new_lyrics = request.form['lyrics']
        new_note = request.form['note']  # Obtener la nueva nota del formulario
        new_classification = request.form['classification']  # Obtener la nueva clasificación del formulario
        # Actualizar los valores de letras, nota y clasificación en la canción
        song.lyrics = new_lyrics
        song.note = new_note
        song.classification = new_classification
        db.session.commit()  # Guardar los cambios en la base de datos
        return redirect(url_for('index'))
    return render_template('letra.html', song=song, editable=True)

@app.route('/delete/<int:song_id>', methods=['POST', 'DELETE'])
def delete_song(song_id):
    if request.method == 'DELETE' or request.form.get('_method') == 'DELETE':
        song = Song.query.get_or_404(song_id)
        db.session.delete(song)
        db.session.commit()
        return redirect(url_for('index'))
    else:
        return 'Method Not Allowed', 405

if __name__ == '__main__':
    app.run(debug=True)