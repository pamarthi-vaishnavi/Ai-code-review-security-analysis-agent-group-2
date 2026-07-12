package com.vaishnavi.code_review_agent;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import javax.tools.*;
import java.util.Arrays;
import java.util.List;
import java.io.File;
import java.io.FileWriter;

@Service
public class CodeValidationService {

    private final List<String> supportedExtensions = Arrays.asList("java", "py");

    // Existing file upload method
    public String validateCode(MultipartFile file) {
        if (file.isEmpty()) return "Error: The file is empty.";
        try {
            File tempFile = File.createTempFile("temp", "." + file.getOriginalFilename().substring(file.getOriginalFilename().lastIndexOf(".") + 1));
            file.transferTo(tempFile);
            return (file.getOriginalFilename().endsWith(".java")) ? validateJavaSyntax(tempFile) : validatePythonSyntax(tempFile);
        } catch (Exception e) { return "Error: " + e.getMessage(); }
    }

    // New method for direct code paste
    public String validateCodeText(String code, String language) {
        try {
            File tempFile = File.createTempFile("temp", language.equals("java") ? ".java" : ".py");
            try (FileWriter writer = new FileWriter(tempFile)) { writer.write(code); }
            return language.equals("java") ? validateJavaSyntax(tempFile) : validatePythonSyntax(tempFile);
        } catch (Exception e) { return "Error during validation: " + e.getMessage(); }
    }

    // Refactored helper methods accepting File object
    private String validateJavaSyntax(File file) {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) return "Error: Java compiler not found.";
        int result = compiler.run(null, null, null, file.getPath());
        file.delete();
        return (result == 0) ? "Syntax check passed!" : "Syntax error detected in Java file.";
    }
    private String validatePythonSyntax(File file) {
        try {
            ProcessBuilder pb = new ProcessBuilder("python", "-m", "py_compile", file.getPath());
            int exitCode = pb.start().waitFor();
            file.delete();
            return (exitCode == 0) ? "Syntax check passed!" : "Syntax error detected in Python file.";
        } catch (Exception e) { return "Error: " + e.getMessage(); }
    }
}