from flask import Flask, request, render_template, jsonify
import fitz  # PyMuPDF pour extraire du texte des PDF
import difflib
import deepdiff
from rapidfuzz import fuzz
import pandas as pd
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_text_from_pdf(pdf_path):
    """Extrait le texte d'un fichier PDF et le divise en lignes."""
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text("text") for page in doc])
    return text.splitlines()

def compare_with_difflib(text1, text2):
    """Compare deux textes ligne par ligne avec difflib."""
    diff = difflib.ndiff(text1, text2)
    return "\n".join(diff)

def compare_with_deepdiff(text1, text2):
    """Compare deux textes avec DeepDiff pour voir les différences plus globales."""
    return deepdiff.DeepDiff(text1, text2, ignore_order=True)

def compare_with_fuzzy(text1, text2):
    """Compare les textes ligne par ligne en utilisant un score de similarité avec rapidfuzz."""
    fuzzy_results = []
    max_length = max(len(text1), len(text2))

    for i in range(max_length):
        line1 = text1[i] if i < len(text1) else ""
        line2 = text2[i] if i < len(text2) else ""
        score = fuzz.ratio(line1, line2)
        fuzzy_results.append({"Texte 1": line1, "Texte 2": line2, "Score de similarité": score})
    
    return fuzzy_results

@app.route("/", methods=["GET", "POST"])
def upload_files():
    if request.method == "POST":
        file1 = request.files["pdf1"]
        file2 = request.files["pdf2"]

        if file1 and file2:
            path1 = os.path.join(UPLOAD_FOLDER, "uploaded1.pdf")
            path2 = os.path.join(UPLOAD_FOLDER, "uploaded2.pdf")
            file1.save(path1)
            file2.save(path2)

            # Extraction du texte des PDF
            text1 = extract_text_from_pdf(path1)
            text2 = extract_text_from_pdf(path2)

            # Comparaison avec différentes méthodes
            diff_difflib = compare_with_difflib(text1, text2)
            diff_deepdiff = compare_with_deepdiff(text1, text2)
            diff_fuzzy = compare_with_fuzzy(text1, text2)

            # Convertir les résultats Fuzzy en HTML
            fuzzy_df = pd.DataFrame(diff_fuzzy)
            fuzzy_html = fuzzy_df.to_html()

            return render_template("result.html", 
                                   difflib_diff=diff_difflib,
                                   deepdiff_diff=diff_deepdiff,
                                   fuzzy_html=fuzzy_html)
    
    return render_template("upload.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=os.getenv("PORT", default=5000))
