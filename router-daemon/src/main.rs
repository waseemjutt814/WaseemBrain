mod expert_loader;
mod metrics;
mod router;
mod session;

use std::env;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

use expert_loader::ExpertFileCache;
use metrics::Metrics;
use router::OnnxRouter;
use tokio::sync::Mutex;
use tonic::{transport::Server, Request, Response, Status};

pub mod proto {
    tonic::include_proto!("router");
}

use proto::expert_service_server::{ExpertService, ExpertServiceServer};
use proto::router_service_server::{RouterService, RouterServiceServer};
use proto::{EvictRequest, EvictResponse, MapRequest, MapResponse, RouterDecision, RouterRequest};

#[derive(Clone)]
struct RouterGrpcService {
    router: Arc<Mutex<OnnxRouter>>,
    metrics: Arc<Metrics>,
}

#[derive(Clone)]
struct ExpertGrpcService {
    cache: Arc<Mutex<ExpertFileCache>>,
}

#[tonic::async_trait]
impl RouterService for RouterGrpcService {
    async fn decide(&self, request: Request<RouterRequest>) -> Result<Response<RouterDecision>, Status> {
        self.metrics.record_request();
        let decision = self
            .router
            .lock()
            .await
            .decide(request.into_inner())
            .map_err(|err| Status::internal(err.to_string()))?;
        Ok(Response::new(decision))
    }
}

#[tonic::async_trait]
impl ExpertService for ExpertGrpcService {
    async fn map_expert(&self, request: Request<MapRequest>) -> Result<Response<MapResponse>, Status> {
        let request = request.into_inner();
        let path = PathBuf::from(request.file_path);
        let mut cache = self.cache.lock().await;
        cache
            .ensure_mapped(&request.expert_id, &path)
            .map_err(|err| Status::internal(err.to_string()))?;
        Ok(Response::new(MapResponse {
            mapped: true,
            mapped_count: cache.mapped_count() as u32,
        }))
    }

    async fn evict_expert(&self, request: Request<EvictRequest>) -> Result<Response<EvictResponse>, Status> {
        let request = request.into_inner();
        let mut cache = self.cache.lock().await;
        let evicted = cache.evict(&request.expert_id);
        Ok(Response::new(EvictResponse {
            evicted,
            mapped_count: cache.mapped_count() as u32,
        }))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let grpc_port = env::var("GRPC_PORT").unwrap_or_else(|_| "50051".to_string());
    let addr: SocketAddr = format!("0.0.0.0:{grpc_port}").parse()?;
    let model_path = PathBuf::from(env::var("ROUTER_MODEL_PATH").unwrap_or_else(|_| "./experts/router.json".to_string()));
    let threshold = env::var("ROUTER_CONFIDENCE_THRESHOLD")
        .ok()
        .and_then(|raw| raw.parse::<f32>().ok())
        .unwrap_or(0.7);

    let router = Arc::new(Mutex::new(OnnxRouter::new(&model_path, threshold)?));
    let metrics = Arc::new(Metrics::default());
    let cache = Arc::new(Mutex::new(ExpertFileCache::default()));

    let router_service = RouterGrpcService { router, metrics };
    let expert_service = ExpertGrpcService { cache };

    Server::builder()
        .add_service(RouterServiceServer::new(router_service))
        .add_service(ExpertServiceServer::new(expert_service))
        .serve(addr)
        .await?;

    Ok(())
}
