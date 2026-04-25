variable "project_id" {
  type        = string
  description = "GCP project id"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Region for buckets and Vertex"
}

variable "bucket_data_name" {
  type        = string
  description = "Globally unique GCS bucket name for datasets"
}

variable "bucket_ckpt_name" {
  type        = string
  description = "Globally unique GCS bucket name for checkpoints"
}

variable "training_sa_id" {
  type        = string
  default     = "jarvis-training"
  description = "Service account id (without domain)"
}
