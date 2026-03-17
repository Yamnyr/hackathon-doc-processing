from flask import Flask, render_template

# Initialisation de l'application Flask
app = Flask(__name__,)  # Correctement séparé

# Route pour la page d'accueil
@app.route('/home.html')
def home():
    return render_template('home.html')

# Route pour la page d'upload
@app.route('/upload.html')
def upload():
    return render_template('upload.html')

# Route pour la page de documents
@app.route('/mes_documents.html')
def documents():
    return render_template('documents.html')

# Route pour la page de SIRET
@app.route('/siret.html')
def siret():
    return render_template('siret.html')

# Route pour la page de test
@app.route('/kbis.html')
def kbis():
    return render_template('kbis.html')

# Route pour la page de test
@app.route('/facture.html')
def facture():
    return render_template('facture.html')

 # Route pour la page de test
@app.route('/devis.html')
def devis():
     return render_template('devis.html')

 # Route pour la page de test
@app.route('/rib.html')
def rib():
     return render_template('rib.html')

 # Route pour la page de test
@app.route('/ursaff.html')
def ursaff():
     return render_template('ursaff.html')



# Lancement de l'application Flask
if __name__ == '__main__':
    app.run(debug=True)