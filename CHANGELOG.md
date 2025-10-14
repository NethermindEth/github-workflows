# Changelog

## [1.10.0](https://github.com/NethermindEth/github-workflows/compare/v1.9.2...v1.10.0) (2025-10-14)


### Features

* print trivy output as part of the build job ([b5f167a](https://github.com/NethermindEth/github-workflows/commit/b5f167a426b3cb18ad9322ae2c829edc24d4e424))

## [1.9.2](https://github.com/NethermindEth/github-workflows/compare/v1.9.1...v1.9.2) (2025-10-06)


### Bug Fixes

* bump docker/login-action from 3.5.0 to 3.6.0 ([#93](https://github.com/NethermindEth/github-workflows/issues/93)) ([4496e14](https://github.com/NethermindEth/github-workflows/commit/4496e14795c4a55e25be6bcd9c8b0d3e6ba4101c))

## [1.9.1](https://github.com/NethermindEth/github-workflows/compare/v1.9.0...v1.9.1) (2025-10-03)


### Bug Fixes

* remove tag name from image name ([afe37d8](https://github.com/NethermindEth/github-workflows/commit/afe37d8346565ca856c0061fcf28449203774b5a))
* Send fully qualified name for each digest ([c6b1bb8](https://github.com/NethermindEth/github-workflows/commit/c6b1bb8e40a3a1d62e585348ab05c8516bef9be7))

## [1.9.0](https://github.com/NethermindEth/github-workflows/compare/v1.8.0...v1.9.0) (2025-09-11)


### Features

* add skip_attest input to docker promotion workflow ([2b76c67](https://github.com/NethermindEth/github-workflows/commit/2b76c6704a8d58ebc00dc5bd8299493366295f74))


### Bug Fixes

* change skip_attest input type to string in docker promotion workflow ([d65d060](https://github.com/NethermindEth/github-workflows/commit/d65d0604d21e6f8e778ed260b6eb89d42b76d5d0))

## [1.8.0](https://github.com/NethermindEth/github-workflows/compare/v1.7.0...v1.8.0) (2025-09-11)


### Features

* add run_trivy input for Docker workflows ([886662a](https://github.com/NethermindEth/github-workflows/commit/886662ae4c08eff3bc9061081c9afaa8c56797c1))
* enhance docker promotion workflow with source_tag input ([f26eeac](https://github.com/NethermindEth/github-workflows/commit/f26eeac7fc1a0703de57a5ea8f8f1b01f1c260f4))


### Bug Fixes

* update valid environments in docker promotion workflow ([6f29a37](https://github.com/NethermindEth/github-workflows/commit/6f29a3783be9e520bfa7da224752a15f9de94660))

## [1.7.0](https://github.com/NethermindEth/github-workflows/compare/v1.6.0...v1.7.0) (2025-09-10)


### Features

* add fetch-depth input for Docker workflows ([e10d7ee](https://github.com/NethermindEth/github-workflows/commit/e10d7ee9e1b2a395d8912efe509c46d8a2a8c283))

## [1.6.0](https://github.com/NethermindEth/github-workflows/compare/v1.5.1...v1.6.0) (2025-09-10)


### Features

* add source_tag input for Docker promotion workflow ([56464b4](https://github.com/NethermindEth/github-workflows/commit/56464b4989ef36f20a13d8db03fd3d1020a36c4a))

## [1.5.1](https://github.com/NethermindEth/github-workflows/compare/v1.5.0...v1.5.1) (2025-08-15)


### Bug Fixes

* be able to select runner for dockerhub as well ([62b3174](https://github.com/NethermindEth/github-workflows/commit/62b3174ed51b7335fce83882380d53f309bea9e7))

## [1.5.0](https://github.com/NethermindEth/github-workflows/compare/v1.4.3...v1.5.0) (2025-08-14)


### Features

* Add pre-build script support to Docker workflows ([b06cb5b](https://github.com/NethermindEth/github-workflows/commit/b06cb5bc20ca9d9fa5ac63fcb2e199370efb32f4))

## [1.4.3](https://github.com/NethermindEth/github-workflows/compare/v1.4.2...v1.4.3) (2025-08-12)


### Bug Fixes

* Enable recursive submodule checkout ([c8c2b07](https://github.com/NethermindEth/github-workflows/commit/c8c2b07234ec048c7891f593024d60bef2883154))
* Update pull request trigger configuration in build-push-dockerhub-simple.yml ([dba621a](https://github.com/NethermindEth/github-workflows/commit/dba621a224215bd674870ca8da2c6b725b984f75))

## [1.4.2](https://github.com/NethermindEth/github-workflows/compare/v1.4.1...v1.4.2) (2025-07-30)


### Bug Fixes

* Update version to create more tags by default ([4b9db1e](https://github.com/NethermindEth/github-workflows/commit/4b9db1e94c261180090bd2e8970850492220a02a))

## [1.4.1](https://github.com/NethermindEth/github-workflows/compare/v1.4.0...v1.4.1) (2025-07-29)


### Bug Fixes

* update versions and remove jfrog url from image name ([cb6ab7b](https://github.com/NethermindEth/github-workflows/commit/cb6ab7b307e39ebed5b73571859e3088a316d402))

## [1.4.0](https://github.com/NethermindEth/github-workflows/compare/v1.3.4...v1.4.0) (2025-07-28)


### Features

* add customizable runner input ([29d290e](https://github.com/NethermindEth/github-workflows/commit/29d290ee7bd5b9abec14a3fbf58d59278ece97f1))


### Bug Fixes

* Update versions ([3c8f5b9](https://github.com/NethermindEth/github-workflows/commit/3c8f5b9ffe4a2a5260f75ac276a6e12a423d57cc))

## [1.3.4](https://github.com/NethermindEth/github-workflows/compare/v1.3.3...v1.3.4) (2025-06-26)


### Bug Fixes

* typo in attestation code ([f53acdf](https://github.com/NethermindEth/github-workflows/commit/f53acdf8822fab3f482cde0d76a455766ba754ce))

## [1.3.3](https://github.com/NethermindEth/github-workflows/compare/v1.3.2...v1.3.3) (2025-06-26)


### Bug Fixes

* set correct attestation subject name ([cffecb3](https://github.com/NethermindEth/github-workflows/commit/cffecb317be4f9172b7ffd431724656aa224a4bc))

## [1.3.2](https://github.com/NethermindEth/github-workflows/compare/v1.3.1...v1.3.2) (2025-06-10)


### Bug Fixes

* Correct JFrog URL format in docker-promote-jfrog.yaml ([2dd5524](https://github.com/NethermindEth/github-workflows/commit/2dd5524de3d058fa0208c785beb35cbcd56dfc5f))

## [1.2.1](https://github.com/NethermindEth/github-workflows/compare/v1.2.0...v1.2.1) (2025-06-04)


### Bug Fixes

* Correct typo in error message for repo name determination in docker-build-push-jfrog.yaml ([afe4686](https://github.com/NethermindEth/github-workflows/commit/afe4686d2137c3847aac479bfee8bded80d4c229))

## [1.2.0](https://github.com/NethermindEth/github-workflows/compare/v1.1.1...v1.2.0) (2025-06-04)


### Features

* Add Docker build and push workflows for Docker Hub and JFrog Artifactory ([#59](https://github.com/NethermindEth/github-workflows/issues/59)) ([f68fb7d](https://github.com/NethermindEth/github-workflows/commit/f68fb7d4db77ea7696bd99b216c4f565e59562c5))
* added acctions: docker-build-and-push-image and jfrog-build-pub… ([8d0255b](https://github.com/NethermindEth/github-workflows/commit/8d0255b62ec5f41f7ace640012863399d12deb08))
* added acctions: docker-build-and-push-image and jfrog-build-publish ([1737e3e](https://github.com/NethermindEth/github-workflows/commit/1737e3e52bc41d0af575168326626503be60b11a))
* added pipeline workflows ([cae1f0a](https://github.com/NethermindEth/github-workflows/commit/cae1f0ae2615be32bd362da4a2714666936c6f0b))
* added pipeline workflows ([56e7c72](https://github.com/NethermindEth/github-workflows/commit/56e7c72c5c92c5c9e99dad0999e73fc520f34efd))
* switched docker login credentials to oidc token ([9d435d5](https://github.com/NethermindEth/github-workflows/commit/9d435d513f2a6778256ccf5cb191bf18b5690aed))
* updated pipeline-ci-pull-request ([621b1be](https://github.com/NethermindEth/github-workflows/commit/621b1be8525f2b5776508cbfe43d9ca7f4d9592b))

## [1.1.1](https://github.com/NethermindEth/github-workflows/compare/v1.1.0...v1.1.1) (2025-04-15)


### Bug Fixes

* add missing issues permission for release please ([912186b](https://github.com/NethermindEth/github-workflows/commit/912186bd22df1fae66c0e06c69fe292d1319c7ea))
* add missing issues permission for release please ([29a013e](https://github.com/NethermindEth/github-workflows/commit/29a013eaa7b9b1b0fd13af869088f2fc8e3a7e24))

## [1.1.0](https://github.com/NethermindEth/github-workflows/compare/v1.0.0...v1.1.0) (2025-04-14)


### Features

* docker build improvements ([459b8fa](https://github.com/NethermindEth/github-workflows/commit/459b8fa87abefe69cb29f02f6d19d9f4092d0044))

## 1.0.0 (2025-04-14)


### Features

* add docker build and push workflow (v2) ([#36](https://github.com/NethermindEth/github-workflows/issues/36)) ([15c8035](https://github.com/NethermindEth/github-workflows/commit/15c803568150ca3c83b3d6cd3f8c7f9f0f3d578b))
* added authentication for module validation ([876eae9](https://github.com/NethermindEth/github-workflows/commit/876eae9304ee44c264fd798babc5c3be7eecde23))
* added dependabot for GitHub Actions ([41fc3d1](https://github.com/NethermindEth/github-workflows/commit/41fc3d13ec492dd661795a0ec352d2a261897826))
* added output prs_created ([9592746](https://github.com/NethermindEth/github-workflows/commit/9592746c48d74ad4af676b0c6e083e0f9396dccd))
* added publish-terraform-module workflow ([4c3e6e5](https://github.com/NethermindEth/github-workflows/commit/4c3e6e5a284cf05177da585a67042c437b83d2d1))
* Added rlease workflow with 'release-please' ([835ad6f](https://github.com/NethermindEth/github-workflows/commit/835ad6fb56975e76f2f96bc9cdc77f81a46ab7ec))
* added workflow job for terraform module release ([12bf0fc](https://github.com/NethermindEth/github-workflows/commit/12bf0fc037eb8538391378a820f54d653bee7b7b))
* **commitizen:** added bump workflow ([ee4d1f5](https://github.com/NethermindEth/github-workflows/commit/ee4d1f5fd4bc761742b0b4e3a97768a16b7d3a6b))
* create and push tag ([f949088](https://github.com/NethermindEth/github-workflows/commit/f949088a2b54693a908f8d5d3e45bf58d8138399))
* docker build/promote image workflows ([#4](https://github.com/NethermindEth/github-workflows/issues/4)) ([a7e3ad1](https://github.com/NethermindEth/github-workflows/commit/a7e3ad1a276cbc355f2f0f8d3c2c6844477f2a4f))
* enhance Docker promotion and publishing workflows ([#35](https://github.com/NethermindEth/github-workflows/issues/35)) ([016adb1](https://github.com/NethermindEth/github-workflows/commit/016adb14ddfd17cfbd0c650ae46315eeabf1be0b))
* helm chart packaging and publish it to jfrog resuable workflow ([#20](https://github.com/NethermindEth/github-workflows/issues/20)) ([266072a](https://github.com/NethermindEth/github-workflows/commit/266072a79c9d0b39c5211e890d9c8802e3f498f6))
* improved pre-commit workflows ([67939d4](https://github.com/NethermindEth/github-workflows/commit/67939d422beafd3c492144166220f4fae8698894))
* **pre-commit:** added download of terraform-docs ([873f9de](https://github.com/NethermindEth/github-workflows/commit/873f9de1b3cef35e6288565e2649d22b9b94030c))
* **pre-commit:** added pre-commit configuration ([c6b9dcc](https://github.com/NethermindEth/github-workflows/commit/c6b9dccc46eac10f64a87e9d9b67548123bfa728))
* **release-please:** added 2 workflows for releasing versions ([bc93c11](https://github.com/NethermindEth/github-workflows/commit/bc93c117a9783eab14672020bd119f4bcb7bf49d))
* **release:** added output release_created ([f530ffc](https://github.com/NethermindEth/github-workflows/commit/f530ffce9a9691e07d03763f59c8c7ce13e921b9))
* **tflint:** added tflint installation ([7f55375](https://github.com/NethermindEth/github-workflows/commit/7f553753350d9968372cef59727fc235981b7574))
* use release please action for semantic versioning ([c2954e7](https://github.com/NethermindEth/github-workflows/commit/c2954e7d8a3ed312af2e80872fb6a58b971b0d00))
* use release please instead ([f8f872f](https://github.com/NethermindEth/github-workflows/commit/f8f872fb8857de2713865358d40338cef1f03520))


### Bug Fixes

* add missing permissions ([14c1f5c](https://github.com/NethermindEth/github-workflows/commit/14c1f5cced591c32d8c50c27e99556ebe5855744))
* add missing permissions ([e008b6e](https://github.com/NethermindEth/github-workflows/commit/e008b6e1b086b46999dfb1f8ad8faa2466a3b117))
* added missing files ([00fd13a](https://github.com/NethermindEth/github-workflows/commit/00fd13a444e30b85c71d5f5f2d1dd89081e4facc))
* **compute-name:** fixet terraform module and provider names ([3962bd0](https://github.com/NethermindEth/github-workflows/commit/3962bd09087a60387b3c0876c1436bc1d8a987fc))
* **compute-terraform-module-name:** updated logic ([814f727](https://github.com/NethermindEth/github-workflows/commit/814f7279e2f7a51f7f7d3b175a3669e75f3d6251))
* exclude example dir when publishing modules ([#34](https://github.com/NethermindEth/github-workflows/issues/34)) ([5e04a0b](https://github.com/NethermindEth/github-workflows/commit/5e04a0b6b027b3511c7c9804927dcf144905f914))
* Fixed inputs ([fdafd83](https://github.com/NethermindEth/github-workflows/commit/fdafd8363d273874adc891a2544bfeb99c50211c))
* **jfrog:** addded missing protocol scheme ([c03f176](https://github.com/NethermindEth/github-workflows/commit/c03f1760f9f6520d6726757ad21181eed3afd0fb))
* **job-terraform-release:** added global permissions block ([8f4f276](https://github.com/NethermindEth/github-workflows/commit/8f4f2760f6c15670a453a95f377962c79472e0ed))
* **job-terraform-release:** fixed input name ([237c5d1](https://github.com/NethermindEth/github-workflows/commit/237c5d19fe03f5cd043f3534dbdc3f8340bd2131))
* **job-terraform-release:** removed permissions block ([5bb2a20](https://github.com/NethermindEth/github-workflows/commit/5bb2a20d8e91194269ea0b752f044d850c02b924))
* **job-terraform-release:** removed versions from local workflow refs ([9148808](https://github.com/NethermindEth/github-workflows/commit/9148808e18355ffd57868549601c5575c37f3893))
* labels permissions ([8d7036c](https://github.com/NethermindEth/github-workflows/commit/8d7036c3048eec856543ebf1ebb622e806392767))
* labels permissions ([e735b7a](https://github.com/NethermindEth/github-workflows/commit/e735b7a0f0791be46423b69fcbfb4c8d56246245))
* name ([b57d454](https://github.com/NethermindEth/github-workflows/commit/b57d45478ab543cdd749737ec7b349bda1fa3e69))
* **publish-tf-module:** updated provider name ([9b9ff4f](https://github.com/NethermindEth/github-workflows/commit/9b9ff4f29d1d9ff9a90ac737167b96b823b54003))
* **release:** removed not needed inputs ([72971a3](https://github.com/NethermindEth/github-workflows/commit/72971a30dfe529e6ab2dce65a183bfd901cd4dca))
* resolved problem with repository name contaning multiple dashes ([68873e7](https://github.com/NethermindEth/github-workflows/commit/68873e78a13f2f16bf4a6f5e5bd59c688717e3ea))
* **terraform-docs:** create folder if not present ([40940be](https://github.com/NethermindEth/github-workflows/commit/40940beb91d2ff55c0cae186bb26775a57c7368f))
* **terraform-docs:** fixed download process of binary ([0eecf0d](https://github.com/NethermindEth/github-workflows/commit/0eecf0da4b71add2d85791d79a6adbc03bb46967))
* **terraform-docs:** fixed installation script ([01e6587](https://github.com/NethermindEth/github-workflows/commit/01e6587383c97453c36b10c1de5d132d9b9c31e7))
* updated JFROG_URL with connection type ([6f34087](https://github.com/NethermindEth/github-workflows/commit/6f340873a1b4d799dcb5d984c13c291b5a129c8b))
* updated secret setup ([2a4ad8a](https://github.com/NethermindEth/github-workflows/commit/2a4ad8a7f6d60728559b68774581697856da7c14))
