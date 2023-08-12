# latest_torch

Metapackage to make installing latest torch easier

Not tested on mac and linux.

## Usage

```sh
pip install --no-deps latest_torch
pip install latest_torch
```

기본값으로 CUDA 패키지 중 가장 최신버전을 설치합니다.

백엔드를 변경하려는 경우, `LATEST_TORCH_BACKEND` 환경변수를 설정하세요.

```sh
LATEST_TORCH_BACKEND=cu117 pip install latest_torch
```

- example:
  - cu117, cpu, rocm5.4.2
