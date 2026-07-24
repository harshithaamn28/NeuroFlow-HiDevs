CREATE FUNCTION current_pipeline_id() RETURNS UUID AS $$
BEGIN
  RETURN NULLIF(current_setting('app.pipeline_id', true), '')::UUID;
EXCEPTION WHEN invalid_text_representation THEN
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Documents belong to a pipeline.
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY documents_pipeline_policy ON documents
  USING (pipeline_id = current_pipeline_id());

-- Chunks inherit pipeline isolation through their documents.
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
CREATE POLICY chunks_pipeline_policy ON chunks
  USING (
    document_id IN (
      SELECT id FROM documents WHERE pipeline_id = current_pipeline_id()
    )
  );

-- Pipeline runs belong to a pipeline.
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY pipeline_runs_pipeline_policy ON pipeline_runs
  USING (pipeline_id = current_pipeline_id());

-- Evaluations are scoped through the run.
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
CREATE POLICY evaluations_pipeline_policy ON evaluations
  USING (
    run_id IN (
      SELECT id FROM pipeline_runs WHERE pipeline_id = current_pipeline_id()
    )
  );

-- Training pairs are scoped through the run.
ALTER TABLE training_pairs ENABLE ROW LEVEL SECURITY;
CREATE POLICY training_pairs_pipeline_policy ON training_pairs
  USING (
    run_id IN (
      SELECT id FROM pipeline_runs WHERE pipeline_id = current_pipeline_id()
    )
  );
