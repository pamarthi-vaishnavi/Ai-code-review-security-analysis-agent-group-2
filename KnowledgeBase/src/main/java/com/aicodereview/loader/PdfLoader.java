package com.aicodereview.loader;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

@Component
public class PdfLoader {

    private final String[] pdfFiles = {
            "knowledge-base/OWASP_Top10.pdf",
            "knowledge-base/Secure_Coding_Practices.pdf",
            "knowledge-base/Java_Security_Cheat_Sheet.pdf",
            "knowledge-base/SQL_Injection_Prevention.pdf",
            "knowledge-base/XSS_Prevention.pdf",
            "knowledge-base/CSRF_Prevention.pdf",
            "knowledge-base/Authentication_Cheat_Sheet.pdf",
            "knowledge-base/Password_Storage_Cheat_Sheet.pdf",
            "knowledge-base/Input_Validation_Cheat_Sheet.pdf",
            "knowledge-base/Logging_Cheat_Sheet.pdf",
            "knowledge-base/CWE_Top25.pdf"
    };

    public List<String> loadPdfContents() {

        List<String> documents = new ArrayList<>();

        PDFTextStripper stripper = new PDFTextStripper();

        for (String pdf : pdfFiles) {

            try (InputStream inputStream = getClass().getClassLoader().getResourceAsStream(pdf)) {

                if (inputStream == null) {
                    System.out.println("PDF not found: " + pdf);
                    continue;
                }

                PDDocument document = Loader.loadPDF(inputStream.readAllBytes());

                String text = stripper.getText(document);

                documents.add(text);

                document.close();

                System.out.println("Loaded: " + pdf);

            } catch (IOException e) {

                System.out.println("Error reading: " + pdf);

                e.printStackTrace();
            }
        }

        return documents;
    }
}