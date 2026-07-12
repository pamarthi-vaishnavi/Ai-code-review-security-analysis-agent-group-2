package com.vaishnavi.code_review_agent;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.util.Map;

@RestController
@RequestMapping("/api/code")
public class CodeSubmissionController {

    @Autowired
    private CodeValidationService validationService;

    @PostMapping("/submit")
    public ResponseEntity<String> handleCodeSubmission(@RequestBody String codeSnippet) {
        if (codeSnippet == null || codeSnippet.isEmpty()) {
            return ResponseEntity.badRequest().body("No code provided.");
        }
        return ResponseEntity.ok("Code received successfully!");
    }

    @PostMapping("/upload")
    public ResponseEntity<String> uploadCode(@RequestParam("file") MultipartFile file) {
        String result = validationService.validateCode(file);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/submit-text")
    public String submitCodeText(@RequestBody Map<String, String> payload) {
        String code = payload.get("code");
        String language = payload.get("language");
        return validationService.validateCodeText(code, language);
    }
}
