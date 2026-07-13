package com.aicodereview.service;

import org.springframework.stereotype.Service;

import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class SimilaritySearchService {

    private final EmbeddingService embeddingService;
    private final VectorStoreService vectorStoreService;

    public SimilaritySearchService(EmbeddingService embeddingService,
                                   VectorStoreService vectorStoreService) {

        this.embeddingService = embeddingService;
        this.vectorStoreService = vectorStoreService;
    }

    public List<String> search(String question, int topK) {

        float[] queryEmbedding = embeddingService.generateEmbedding(question);

        return vectorStoreService.getAllDocuments()
                .stream()
                .sorted(Comparator.comparingDouble(
                        doc -> -cosineSimilarity(queryEmbedding, doc.getEmbedding())))
                .limit(topK)
                .map(VectorStoreService.VectorDocument::getText)
                .collect(Collectors.toList());
    }

    private double cosineSimilarity(float[] a, float[] b) {

        double dot = 0;
        double normA = 0;
        double normB = 0;

        for (int i = 0; i < a.length; i++) {

            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }

        return dot / (Math.sqrt(normA) * Math.sqrt(normB));
    }
}