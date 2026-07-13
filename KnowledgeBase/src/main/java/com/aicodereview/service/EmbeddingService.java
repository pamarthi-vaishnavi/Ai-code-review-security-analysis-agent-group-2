package com.aicodereview.service;

import org.springframework.ai.document.Document;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class EmbeddingService {

    private final EmbeddingModel embeddingModel;

    public EmbeddingService(EmbeddingModel embeddingModel) {
        this.embeddingModel = embeddingModel;
    }

    /**
     * Generate embedding for a single text chunk.
     */
    public float[] generateEmbedding(String text) {

    System.out.println("Generating embedding...");

    Document document = new Document(text);

    List<float[]> embeddings = embeddingModel.embed(List.of(document.getText()));

    System.out.println("Embedding generated.");

    return embeddings.getFirst();
   }

}