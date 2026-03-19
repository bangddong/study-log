---
emoji: "🚀"
title: "API 개발 기본"
date: 2025-03-19 00:00:00
update: 2025-03-19 00:00:00
tags:
  - Spring
  - JPA
series: "스프링 부트와 JPA 활용 2"
---

## 회원 등록 API

**MemberApiController**

```java
@RestController
@RequiredArgsConstructor
public class MemberApiController {

	private final MemberService memberService;

	@PostMapping("/api/v1/members")
	public CreateMemberResponse saveMemberV1(@RequestBody @Valid Member member) {
		Long id = memberService.join(member);
		return new CreateMemberResponse(id);
	}

	@Data
	static class CreateMemberResponse {
		private Long id;

		public CreateMemberResponse(Long id) {
			this.id = id;
		}
	}

}
```

### V1 엔티티를 Request Body에 직접 매핑

- **문제점**
    - 엔티티에 프레젠테이션 계층을 위한 로직이 추가됨
    - 엔티티에 API 검증을 위한 로직이 들어감 (@Valid 관련)
    - 실무에서는 회원 엔티티를 위한 API가 다양하게 만들어지는데, 한 엔티티에 각각의 API를 위한 모든 요청 요구사항을 담기는 어려움
    - 엔티티가 변경되면 API 스펙이 변함
- **결론**
    - API 요청 스펙에 맞추어 별도의 DTO를 파라미터로 받아야 함

### V2 엔티티 대신에 DTO를 RequestBody에 매핑

**MemberApiController**

```java
	@PostMapping("/api/v2/members")
	public CreateMemberResponse saveMemberV2(@RequestBody @Valid CreateMemberRequest request) {
		Member member = new Member();
		member.setName(request.getName());

		Long id = memberService.join(member);
		return new CreateMemberResponse(id);
	}

	@Data
	static class CreateMemberRequest {
		private String name;
	}
```

- `CreateMemberRequest`를 `Member` 엔티티 대신에 RequestBody와 매핑
- 엔티티와 프레젠테이션 계층을 분리 가능
- 엔티티와 API 스펙 명확하게 분리 가능
- 엔티티가 변해도 API 스펙은 영향 없음

`※ 실무에서는 엔티티를 API 스펙에 노출하지 않습니다!`

## 회원 수정 API

**MemberApiController**

```java
@PatchMapping("/api/v2/members/{id}")
public UpdateMemberResponse updateMemberV2(
	@PathVariable("id") Long id,
	@RequestBody @Valid UpdateMemberRequest request
) {
	memberService.update(id, request.getName());
	Member findMember = memberService.findOne(id);
	return new UpdateMemberResponse(findMember.getId(), findMember.getName());
}

@Data
static class UpdateMemberRequest {
	private String name;
}

@Data
@AllArgsConstructor
static class UpdateMemberResponse {
	private Long id;
	private String name;
}
```

**MemberService**

```java
/**
 * 회원 수정
 */
@Transactional
public void update(Long id, String name) {
  // 변경 감지를 통합 Update
	Member member = memberRepository.findOne(id);
	member.setName(name);
}
```

`※ 수정 요청이기에 PUT을 생각할 수 있지만 전체 수정이 아닌 일부 수정이기에 POST나 PATCH가 조금 더 REST한 스타일임`

## 회원 조회 API

### 회원조회 V1: 응답 값으로 엔티티를 직접 외부에 노출

**MemberApiController**

```java
@GetMapping("/api/v1/members")
public List<Member> saveMemberV1() {
	return memberService.findMembers();
}
```

- **문제점**
    - 엔티티에 프레젠테이션 계층을 위한 로직이 추가됨
    - 기본적으로 엔티티의 모든 값이 노출됨
    - 응답 스펙을 맞추기 위해 로직이 추가됨 (@JsonIgnore, 별도의 뷰 로직 등)
    - 실무에서는 같은 엔티티에 대해 API가 용도에 따라 다양한데, 한 엔티티에서 각 API 응답 로직을 처리하기 어려움
    - 엔티티가 변경되면 API 스펙이 변경됨
    - 컬렉션을 직접 반환시 향후 API 스펙 변경하기 어려움
- 결론
    - API 응답 스펙에 맞추어 별도의 DTO를 반환

### 엔티티 대신 DTO를 RequestBody에 매핑

```java
@GetMapping("/api/v2/members")
public Result saveMemberV2() {
	List<Member> findMembers = memberService.findMembers();
	List<MemberDto> collect = findMembers.stream()
		.map(m -> new MemberDto(m.getName()))
		.toList();

	return new Result(collect);
}

@Data
@AllArgsConstructor
static class Result<T> {
	private T data;
}

@Data
@AllArgsConstructor
static class MemberDto {
	private String name;
}
```

- 엔티티를 DTO로 변환해서 반환
- 엔티티가 변해도 API 스펙 영향없음
- 추가로 `Result` 클래스로 컬렉션을 감싸 향후 필요한 필드 추가 가능

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/ZmrMB