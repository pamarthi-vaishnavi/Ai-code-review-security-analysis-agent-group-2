package com.aicodereview.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import com.aicodereview.rag.KnowledgeIndexer;

@RestController
public class KnowledgeController {

    @Autowired
    private KnowledgeIndexer knowledgeIndexer;

    @GetMapping("/load-pdfs")
    public String loadPdfs() {

        knowledgeIndexer.buildKnowledgeBase();

        return "Knowledge Base Created Successfully";
    }
}