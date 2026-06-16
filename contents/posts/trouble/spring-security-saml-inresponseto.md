---
title: Spring Security SAML InResponseTo 검증 실패 — 동작 원리 완전 분석
date: '2026-06-16'
tags:
  - Spring
  - Troubleshooting
series: null
emoji: "\U0001F510"
---

Spring Boot 3.x로 버전을 올린 다음 날, SAML 로그인이 터졌습니다. 한 달 동안 잘 돌던 코드인데요. 프레임워크 버전 하나 올렸을 뿐인데 로그에 이게 찍혔습니다.


```plain text
Valid InResponseTo was not available from the validation context,
unable to evaluate SubjectConfirmationData@InResponseTo
```


에러 메시지만 보고는 원인을 도저히 파악할 수가 없었습니다. 🤔 SAML 스펙 문제인가, 제 설정 문제인가, Spring Security가 뭔가 바꾼 건가. 구글을 다 뜯어봐도 맨땅에 헤딩이었습니다. 결국 코드를 직접 파헤치기 시작했고, 그렇게서야 정확한 원인을 찾아낼 수 있었습니다. 이 글은 그 추적 과정을 정리한 것입니다.


---


## SP-Initiated SAML 흐름은 이렇게 동작한다


문제를 이해하려면 먼저 SP-Initiated SSO 흐름 전체를 봐야 합니다.


```plain text
[브라우저]            [Spring Security]                    [Entra ID]
    |
    |-- GET /api/saml2/authenticate/entra-id?redirect_uri=.. -->
    |                  |
    |     ① AuthnRequest 생성 (ID: _abc123)
    |     ② AuthnRequest를 HTTP 세션에 저장
    |     ③ RelayState = redirect_uri 값으로 설정
    |                  |
    |<-- 302 Entra ID URL (SAMLRequest + RelayState 포함) ------
    |
    |-- GET login.microsoftonline.com (SAMLRequest 전달) ------>
    |
    |    (사용자 로그인)
    |
    |<-- POST /api/login/saml2/sso/entra-id (SAMLResponse + RelayState)
    |                  |
    |     ④ SAMLResponse 파싱
    |     ⑤ InResponseTo 검증  ← ★ 여기서 실패
    |     ⑥ Assertion 검증
    |     ⑦ CustomSamlAuthenticationSuccessHandler 호출
```


핵심은 **②번 저장과 ⑤번 조회 사이에 단절이 생긴다는 것**입니다.


---


## ② 세션 저장 — `HttpSessionSaml2AuthenticationRequestRepository`


Spring Security는 AuthnRequest를 HTTP 세션에 저장합니다.


```java
// HttpSessionSaml2AuthenticationRequestRepository 내부
public void saveAuthenticationRequest(
        AbstractSaml2AuthenticationRequest authenticationRequest,
        HttpServletRequest request, HttpServletResponse response) {
    // key: "org.springframework.security.saml2.savedAuthnRequest"
    request.getSession().setAttribute(SAML2_AUTHN_REQUEST_ATTR_NAME, authenticationRequest);
}
```


AuthnRequest 전체가 현재 요청의 HTTP 세션에 저장되고, 그 세션의 `JSESSIONID`는 `Set-Cookie` 헤더로 브라우저에 전달됩니다.


여기서 **도메인 스코프**가 중요해집니다. `origin.example.com`에서 요청이 시작됐다면 `JSESSIONID`는 `origin.example.com` 도메인에 귀속됩니다.


---


## ⑤ InResponseTo 검증이 실패하는 정확한 이유


Entra ID가 SAMLResponse를 POST할 때 실제로 일어나는 일입니다.


```plain text
POST https://app.example.com/api/login/saml2/sso/entra-id
Host:   app.example.com
Origin: https://login.microsoftonline.com   ← 크로스 사이트!
Cookie: (없음)                              ← JSESSIONID가 app.example.com 도메인에 없음
```


브라우저의 쿠키 전송 규칙 때문입니다.

- `JSESSIONID`는 `origin.example.com` 세션에서 생성됐습니다.
- 이 쿠키는 `Domain=origin.example.com`으로 스코프가 설정되어 있습니다.
- `app.example.com`으로 POST할 때 브라우저는 이 쿠키를 보내지 않습니다 (다른 도메인).
- Tomcat은 쿠키 없는 요청 → 새 세션 생성 (빈 세션).

결과적으로 Spring Security가 `loadAuthenticationRequest`를 호출하면 이렇게 됩니다.


```java
public AbstractSaml2AuthenticationRequest loadAuthenticationRequest(HttpServletRequest request) {
    // 새로 생성된 빈 세션에는 저장된 AuthnRequest가 없음 → null 반환
    return (AbstractSaml2AuthenticationRequest)
            request.getSession(false)
                   .getAttribute(SAML2_AUTHN_REQUEST_ATTR_NAME);  // null!
}
```


---


## null이 WARN 로그가 되는 경로


`BaseOpenSamlAuthenticationProvider`가 내부적으로 검증 컨텍스트를 구성합니다.


```java
private ValidationContext createValidationContext(
        Saml2AuthenticationToken token,
        Consumer<Map<String, Object>> paramsConsumer) {
    AbstractSaml2AuthenticationRequest storedRequest = token.getAuthenticationRequest();
    // storedRequest = null (세션에서 못 찾았으므로)
    Map<String, Object> params = new HashMap<>();
    if (storedRequest != null) {
        params.put(SAML2_AUTHN_REQUEST_ID, storedRequest.getId());  // 실행 안 됨
    }
    // SAML2_AUTHN_REQUEST_ID가 params에 없는 채로 ValidationContext 생성
    return new ValidationContext(params);
}
```


OpenSAML의 `AbstractSubjectConfirmationValidator`가 검증할 때 이 빈 컨텍스트를 마주칩니다.


```java
protected ValidationResult validateInResponseTo(
        SubjectConfirmationData confirmationData,
        ValidationContext context) {
    String inResponseTo = confirmationData.getInResponseTo();  // "_abc123" (SAMLResponse에서)
    String requestId = (String) context.getStaticParameters()
                                       .get(SAML2_AUTHN_REQUEST_ID);  // null!
    if (requestId == null) {
        // ★ 바로 이 WARN 로그
        context.getValidationFailureMessages().add(
            "Valid InResponseTo was not available from the validation context, " +
            "unable to evaluate SubjectConfirmationData@InResponseTo");
        return ValidationResult.INDETERMINATE;  // INVALID가 아닌 INDETERMINATE
    }
    ...
}
```


`INDETERMINATE`는 검증 실패(`INVALID`)와 다르지만, Spring Security는 이를 전체 assertion 실패로 처리해 인증을 차단합니다.


---


## `CustomCacheSaml2AuthenticationRequestRepository`가 이를 해결하는 원리


HTTP 세션(쿠키 기반) 대신 **서버 메모리**를 저장소로 사용합니다.


```java
// 저장 시 (AuthnRequest 시작 단계)
public void saveAuthenticationRequest(...) {
    String relayState = authenticationRequest.getRelayState();
    // relayState = "https://origin.example.com?device_id=xxx"
    this.cache.put(relayState, authenticationRequest);  // 서버 메모리에 저장
}

// 조회 시 (ACS POST 수신 단계)
public AbstractSaml2AuthenticationRequest loadAuthenticationRequest(HttpServletRequest request) {
    String relayState = request.getParameter("RelayState");
    // Entra ID가 SAMLResponse POST 시 RelayState를 body에 포함해서 전달
    // relayState = "https://origin.example.com?device_id=xxx" (동일 값)
    return this.cache.get(relayState, AbstractSaml2AuthenticationRequest.class);  // 조회 성공!
}
```


어떤 도메인에서 시작하든, 어떤 도메인의 ACS로 오든 **RelayState만 일치하면 AuthnRequest 조회가 가능**합니다. 도메인 간 쿠키 단절 문제를 완전히 우회합니다.


빈으로 등록하면 됩니다.


```java
@Bean
public Saml2AuthenticationRequestRepository<AbstractSaml2AuthenticationRequest> authenticationRequestRepository() {
    return new CustomCacheSaml2AuthenticationRequestRepository();
}
```

> 단, 이 방식은 인메모리이므로 단일 인스턴스 환경에서만 안전합니다. Kubernetes 같은 멀티 파드 환경이라면 `cache` 필드를 Redis 같은 분산 캐시로 교체해야 합니다.

---


## RelayState가 UUID여야 하는 이유


`redirect_uri`가 없는 웹 사용자는 RelayState가 빈 문자열이 됩니다. 동시에 여러 사용자가 로그인하면 캐시 키 충돌이 발생합니다.


```plain text
웹 사용자 A: 저장 key="" → "A의 AuthnRequest"
웹 사용자 B: 저장 key="" → "B의 AuthnRequest"  (A 덮어씀!)
웹 사용자 A: 조회 key="" → "B의 AuthnRequest"  (엉뚱한 값)
```


RelayState를 UUID로 변경하면 이 문제가 사라집니다.


```plain text
웹 사용자 A: 저장 key="uuid-aaa" → "A의 AuthnRequest"
웹 사용자 B: 저장 key="uuid-bbb" → "B의 AuthnRequest"
웹 사용자 A: 조회 key="uuid-aaa" → "A의 AuthnRequest" ✓
```


---


## 6.5.9부터는 코드 줄일 수 있다


이슈를 팔로우하다 발견한 내용입니다. 커스텀 구현체를 만들게 된 배경에는 사실 Spring Security 공식 버그가 있었습니다.


Spring Security에는 `CacheSaml2AuthenticationRequestRepository`가 내장 클래스로 이미 존재했습니다. 그런데 `saveAuthenticationRequest`에서 `relayState`를 request 파라미터에서 읽는 버그가 있었습니다. 저장 시점에 아직 request 파라미터로 세팅되지 않은 상태라 바로 `IllegalArgumentException: relayState must not be null`이 터졌습니다. 커스텀 구현체가 만들어진 것도 이 버그 때문이었습니다.


[PR #18872](https://github.com/spring-projects/spring-security/pull/18872)가 이를 수정했고 2026년 3월 10일에 머지됐습니다. 마일스톤: `6.5.9`


Spring Security 6.5.9 이상이라면 커스텀 구현체 없이 공식 클래스를 바로 쓸 수 있습니다.


```java
@Bean
public Saml2AuthenticationRequestRepository<AbstractSaml2AuthenticationRequest> authenticationRequestRepository() {
    return new CacheSaml2AuthenticationRequestRepository();  // 커스텀 불필요
}
```

> Spring Boot 3.5.x는 Spring Security 6.5.x를 동반합니다. 정확한 패치 버전은 `spring-security.version` 프로퍼티로 확인하세요.

---


## Spring 팀은 이 문제를 어떻게 보고 있나


이슈를 신고하고 컴멘트를 관심있게 지켜봤습니다. 결론을 먼저 말하자면, **현재(2026.06)까지 Spring 팀의 공식 도움은 없습니다.** 딸랑 cc 하나만 남겨줌. 🙄


라벨이 두 개입니다.

- `status: waiting-for-triage` — 아직 triage도 안 됨
- `type: enhancement` — 버그가 아닌 개선 사항으로 분류됨

`@rwinch`(스프링 시큐리티 메인테이너)가 다른 팀원인 `@jzheaux`를 cc한 게 전부입니다. `@jzheaux`는 여전히 응답이 없습니다.


업스트림에서 주목할 만한 코멘트가 하나 있습니다.

> _"우리는 Spring Security가 결국 이 문제를 해결해 줄 것으로 기대했는데, repository 관련 수정이 6.5.x에 들어갈 것 같다"_ — re1709 (2025.07)

다만 2026년 6월 기준 이슈는 여전히 open 상태입니다. 관련된 배경 이슈도 두 개 더 있습니다.

- [#14013](https://github.com/spring-projects/spring-security/issues/14013) — Spring Security 6에서 SameSite=Lax가 기본값으로 바뀐 이슈
- [#14793](https://github.com/spring-projects/spring-security/issues/14793) — `Saml2AuthenticationRequestRepository` 교체 접근법에 대한 논의

커뮤니티 워크어라운드인 `CustomCacheSaml2AuthenticationRequestRepository`가 유일한 대안입니다.


---


## 정리


| 항목      | 내용                                                                             |
| ------- | ------------------------------------------------------------------------------ |
| 에러 원인   | IdP가 다른 도메인 ACS로 POST할 때 JSESSIONID 쿠키가 전송되지 않음                                |
| 근본 원인   | 도메인 간 세션 쿠키 단절 (크로스 사이트 POST + 도메인 스코프 불일치)                                    |
| WARN 경로 | `storedRequest = null` → `SAML2_AUTHN_REQUEST_ID` 누락 → `INDETERMINATE` → 인증 차단 |
| 해결책     | `CustomCacheSaml2AuthenticationRequestRepository` — 세션 대신 서버 메모리 사용            |
| 추가 주의   | RelayState를 UUID로 설정하지 않으면 동시 로그인 시 캐시 키 충돌 발생                                 |
| 스케일 주의  | 인메모리 캐시는 단일 인스턴스 전용, 멀티 파드 환경에서는 분산 캐시 필요                                      |


SAML 인증 실패 메시지가 cryptic해서 원인을 찾기 어렵지만, 실제로는 **세션 쿠키가 도메인 경계를 넘지 못하는 브라우저 정책**에서 비롯된 문제입니다. `HttpSessionSaml2AuthenticationRequestRepository` → `CustomCacheSaml2AuthenticationRequestRepository` 교체 하나로 해결됩니다.


---


## 참고

- [spring-projects/spring-security#17631](https://github.com/spring-projects/spring-security/issues/17631)
