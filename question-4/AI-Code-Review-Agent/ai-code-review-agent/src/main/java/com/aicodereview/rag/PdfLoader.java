package com.aicodereview.rag;

import java.io.File;
import java.io.IOException;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.stereotype.Component;

@Component
public class PdfLoader {

    public String loadAllPdfs() {

        StringBuilder allText = new StringBuilder();

        String folderPath = "src/main/resources/knowledge";

        File folder = new File(folderPath);

        if (!folder.exists()) {
            System.out.println("Knowledge folder not found!");
            return allText.toString();
        }

        File[] pdfFiles = folder.listFiles((dir, name) ->
                name.toLowerCase().endsWith(".pdf"));

        if (pdfFiles == null || pdfFiles.length == 0) {
            System.out.println("No PDF files found.");
            return allText.toString();
        }

        PDFTextStripper stripper = new PDFTextStripper();

        for (File pdf : pdfFiles) {

            System.out.println("\n=========================================");
            System.out.println("Reading: " + pdf.getName());
            System.out.println("=========================================");

            try (PDDocument document = Loader.loadPDF(pdf)) {

                String text = stripper.getText(document);

                System.out.println(text);
                allText.append(text);
                allText.append("\n");

            } catch (IOException e) {
                System.out.println("Error reading: " + pdf.getName());
                e.printStackTrace();
            }
        }

        return allText.toString();
    }
}