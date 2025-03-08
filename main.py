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
    """Extrait le texte d'un fichier PDF avec structure par page."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({
            "page": page_num + 1,
            "content": text.splitlines()
        })
    return pages

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

def compare_pages(pages1, pages2):
    """Compare les PDF page par page pour identifier les différences significatives."""
    results = []
    
    # Déterminer le nombre maximum de pages
    max_pages = max(len(pages1), len(pages2))
    
    for i in range(max_pages):
        page_result = {
            "page_num": i + 1,
            "in_both": True,
            "differences": []
        }
        
        # Vérifier si la page existe dans les deux documents
        if i >= len(pages1):
            page_result["in_both"] = False
            page_result["status"] = "Page uniquement dans le nouveau document"
            results.append(page_result)
            continue
        elif i >= len(pages2):
            page_result["in_both"] = False
            page_result["status"] = "Page uniquement dans l'ancien document"
            results.append(page_result)
            continue
        
        # Pour les pages existant dans les deux documents, comparer ligne par ligne
        text1 = pages1[i]["content"]
        text2 = pages2[i]["content"]
        
        # Calculer un score de similarité global pour la page
        page_similarity = fuzz.ratio("\n".join(text1), "\n".join(text2))
        page_result["similarity"] = page_similarity
        
        # Si la similarité est très élevée, on peut considérer les pages comme identiques
        if page_similarity > 95:
            page_result["status"] = "Pages quasiment identiques"
        elif page_similarity > 80:
            page_result["status"] = "Pages similaires avec quelques modifications"
            # Obtenir les différences détaillées
            diff = list(difflib.ndiff(text1, text2))
            page_result["differences"] = [d for d in diff if d.startswith('+ ') or d.startswith('- ')]
        else:
            page_result["status"] = "Pages significativement différentes"
            # Obtenir les différences détaillées
            diff = list(difflib.ndiff(text1, text2))
            page_result["differences"] = [d for d in diff if d.startswith('+ ') or d.startswith('- ')]
        
        results.append(page_result)
    
    return results

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
            pages1 = extract_text_from_pdf(path1)
            pages2 = extract_text_from_pdf(path2)

            # Faire une comparaison plus structurée
            comparison_results = compare_pages(pages1, pages2)
            
            # Analyse globale du document
            total_pages = len(comparison_results)
            significantly_different = sum(1 for r in comparison_results if r.get("similarity", 0) < 80 or not r["in_both"])
            percent_different = (significantly_different / total_pages) * 100 if total_pages > 0 else 0
            
            # Créer un résumé
            summary = {
                "total_pages": total_pages,
                "significantly_different_pages": significantly_different,
                "percent_different": round(percent_different, 2),
                "recommendation": "Il paraît utile d'acheter la nouvelle version" if percent_different > 20 else "La nouvelle version ne semble pas indispensable"
            }

            return render_template("result.html", 
                                   results=comparison_results,
                                   summary=summary)
    
    return render_template("upload.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=os.getenv("PORT", default=5000))
