output "data_bucket" {
  value = google_storage_bucket.data.url
}

output "checkpoint_bucket" {
  value = google_storage_bucket.checkpoints.url
}

output "training_service_account" {
  value = google_service_account.training.email
}
