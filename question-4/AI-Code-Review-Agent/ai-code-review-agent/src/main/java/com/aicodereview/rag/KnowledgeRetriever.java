package com.aicodereview.rag;

import java.util.List;

import org.springframework.stereotype.Component;

import dev.langchain4j.data.embedding.Embedding;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.store.embedding.EmbeddingMatch;
import dev.langchain4j.store.embedding.EmbeddingSearchRequest;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;

@Component
public class KnowledgeRetriever {

    private final KnowledgeIndexer knowledgeIndexer;

    private final EmbeddingModel embeddingModel;
    private final InMemoryEmbeddingStore<TextSegment> embeddingStore;


    public KnowledgeRetriever(KnowledgeIndexer knowledgeIndexer) {

        this.knowledgeIndexer = knowledgeIndexer;

        this.embeddingModel = knowledgeIndexer.getEmbeddingModel();
        this.embeddingStore = knowledgeIndexer.getEmbeddingStore();
    }


    public String search(String query) {

        Embedding queryEmbedding = embeddingModel
                .embed(query)
                .content();


        EmbeddingSearchRequest request =
                new EmbeddingSearchRequest(
                        queryEmbedding,
                        5,
                        0.7,
                        null
                );


        List<EmbeddingMatch<TextSegment>> matches =
                embeddingStore.search(request)
                .matches();


        StringBuilder result = new StringBuilder();


        for (EmbeddingMatch<TextSegment> match : matches) {

            result.append(match.embedded().text());
            result.append("\n\n");
        }


        return result.toString();
    }
}