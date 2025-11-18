---
emoji: "🚀"
title: "구현 준비"
date: 2024-08-20 13:55:00
update: 2024-08-20 13:55:00
tags:
  - Spring
  - JPA
series: "스프링 부트와 JPA 활용 1"
---

# 구현 준비

JPA에 중점을 두기 위해 아래와 같은 기능들은 구현하지 않습니다.

- 로그인과 권한 관리
- 파라미터 검증과 예외 처리
- 상품은 도서만 사용
- 카테고리 사용 X
- 배송 정보 사용 X

## 아키텍처

![image.png](images/spring-jpa-prepare-implements-1.png)

### Layered 아키텍처 적용

- Controller, web: 웹 계층
- service: 비즈니스 로직, 트랜잭션 처리
- repository: 엔티티 매니저를 사용하여 JPA를 직접 사용하는 계층
- domain: 엔티티가 모여 있는 계층, 모든 계층에서 사용

### 패키지 구조

- domain
- exception
- repository
- service
- web

### 개발 순서

서비스, 레포지토리 계층을 개발하고, 테스트 케이스를 작성해서 검증 후 마지막에 웹 계층 적용

이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗

    https://inf.run/4Sbno