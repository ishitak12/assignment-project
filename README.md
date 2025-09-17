# 📄 PDF → JSON Converter (Streamlit App)

A **Streamlit web application** that extracts **text, tables, and charts** from PDF files and outputs a **structured JSON file**. Ideal for converting reports, invoices, or documents into machine-readable JSON format. This app allows you to preview extracted data and download a complete JSON output.

## 🚀 Features

-  Extract **paragraphs**, **sections**, and **sub-sections** with font-based heuristics.
- Extract **tables** using Camelot, pdfplumber, or reconstructed from word positions.
- Detect **charts and images** in PDFs.
- Download a **complete JSON output** of the PDF.
- Built with **Streamlit**, **PyMuPDF**, **Camelot**, **pdfplumber**.
> **Optional:** For more accurate table extraction using Camelot in "lattice" mode, install **Ghostscript** according to your OS:  
> - **Windows:** Download and install from [Ghostscript](https://www.ghostscript.com/download/gsdnld.html)  
> - **Mac:** `brew install ghostscript`  
> - **Linux:** `sudo apt-get install ghostscript python3-tk`  
>
> **Note:** The app has multiple fallbacks (Camelot "stream" mode, pdfplumber, and word-based table reconstruction). So even if Ghostscript is not installed, the app will still work, though some complex tables might be less accurately extracted.

## 📦 Installation & Setup

Clone the repository and navigate to the project folder:

```bash
git remote add origin https://github.com/ishitak12/assignment-project.git
cd assignment-project

##Install Python dependencies:
pip install -r requirements.txt
streamlit
pymupdf
camelot-py[cv]
pdfplumber
pandas

#Run the Streamlit app:

streamlit run app.py



