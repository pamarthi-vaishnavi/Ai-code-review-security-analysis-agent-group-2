package com.aicodereview.service;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class VectorStoreService {

    public static class VectorDocument {

        private final String text;
        private final float[] embedding;

        public VectorDocument(String text, float[] embedding) {
            this.text = text;
            this.embedding = embedding;
        }

        public String getText() {
            return text;
        }

        public float[] getEmbedding() {
            return embedding;
        }
    }

    private final List<VectorDocument> vectorStore = new ArrayList<>();

    public void addDocument(String text, float[] embedding) {

        vectorStore.add(new VectorDocument(text, embedding));
    }

    public List<VectorDocument> getAllDocuments() {
        return vectorStore;
    }

    public int size() {
        return vectorStore.size();
    }
}