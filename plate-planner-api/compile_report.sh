#!/bin/bash
# Compilation script for 295A Report LaTeX document
# This script compiles the LaTeX document with proper bibliography handling

echo "🔨 Compiling 295A Report Chapters 1 & 2..."
echo ""

# Check if pdflatex is installed
if ! command -v pdflatex &> /dev/null; then
    echo "❌ Error: pdflatex not found!"
    echo "Please install a LaTeX distribution:"
    echo "  - macOS: brew install --cask mactex"
    echo "  - Ubuntu: sudo apt-get install texlive-full"
    echo "  - Or use Overleaf: https://overleaf.com"
    exit 1
fi

# File name
TEXFILE="295A_Report_Chapters_1_2"

# Clean previous builds
echo "🧹 Cleaning previous build files..."
rm -f ${TEXFILE}.aux ${TEXFILE}.log ${TEXFILE}.out ${TEXFILE}.bbl ${TEXFILE}.blg

# First pass
echo "📝 First pass: Generating structure..."
pdflatex -interaction=nonstopmode ${TEXFILE}.tex > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ First pass failed! Check the log file for errors:"
    pdflatex -interaction=nonstopmode ${TEXFILE}.tex | tail -20
    exit 1
fi

# Second pass (for references and citations)
echo "📚 Second pass: Resolving references..."
pdflatex -interaction=nonstopmode ${TEXFILE}.tex > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Second pass failed! Check the log file."
    exit 1
fi

# Check if PDF was created
if [ -f "${TEXFILE}.pdf" ]; then
    echo "✅ Compilation successful!"
    echo ""
    echo "📄 Generated PDF: ${TEXFILE}.pdf"
    echo "📊 File size: $(du -h ${TEXFILE}.pdf | cut -f1)"
    echo "📖 Pages: $(pdfinfo ${TEXFILE}.pdf 2>/dev/null | grep Pages | awk '{print $2}' || echo 'N/A')"
    echo ""
    echo "🎉 Your report is ready!"
    
    # Open PDF if on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "📱 Opening PDF..."
        open ${TEXFILE}.pdf
    fi
else
    echo "❌ PDF generation failed!"
    exit 1
fi

# Clean auxiliary files (optional)
echo ""
read -p "🗑️  Clean auxiliary files? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f ${TEXFILE}.aux ${TEXFILE}.log ${TEXFILE}.out ${TEXFILE}.bbl ${TEXFILE}.blg
    echo "✨ Cleaned!"
fi

echo ""
echo "📚 To view the PDF:"
echo "   open ${TEXFILE}.pdf  (macOS)"
echo "   xdg-open ${TEXFILE}.pdf  (Linux)"
echo "   start ${TEXFILE}.pdf  (Windows)"

