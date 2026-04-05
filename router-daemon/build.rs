fn main() {
    let protoc = protoc_bin_vendored::protoc_bin_path()
        .expect("failed to locate vendored protoc binary");
    std::env::set_var("PROTOC", protoc);
    tonic_build::configure()
        .build_server(true)
        .compile(&["proto/router.proto"], &["proto"])
        .expect("failed to compile protobuf definitions");
}
