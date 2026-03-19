---
emoji: "🚀"
title: "확장기능"
date: 2025-03-31 00:00:00
update: 2025-03-31 00:00:00
tags:
  - Spring
  - JPA
series: "스프링 데이터 JPA"
---

# 사용자 정의 리포지토리 구현

- 스프링 데이터 JPA 리포지토리는 인터페이스만 정의하고 구현체는 스프링이 자동 생성
- 스프링 데이터 JPA가 제공하는 인터페이스를 직접 구현하면 구현해야 하는 기능이 너무 많음
- 다양한 이유로 인터페이스의 메서드를 직접 구현하고 싶다면?
    - JPA 직접 사용(`EntityManger`)
    - 스프링 JDBC Template 사용
    - MyBatis 사용
    - 데이터베이스 직접 사용 등등…
    - Querydsl 사용

## 사용자 정의 인터페이스

```java
public interface MemberRepositoryCustom {
	List<Member> findMemberCustom();
}
```

## 사용자 정의 인터페이스 구현 클래스

```java
@RequiredArgsConstructor
public class MemberRepositoryCustomImpl implements MemberRepositoryCustom{

	private final EntityManager em;

	@Override
	public List<Member> findMemberCustom() {
		return em.createQuery("select m from Member m")
			.getResultList();
	}
}
```

## 사용자 정의 인터페이스 상속

```java
public interface MemberRepository 
	extends JpaRepository<Member, Long>, MemberRepositoryCustom {
}
```

## 사용자 정의 메서드 호출 코드

```java
List<Member> result = memberRepository.findMemberCustom();
```

## 사용자 정의 구현 클래스

- 규칙 : 리포지토리 인터페이스 이름 + `Impl`
    - 다른 이름으로 써도 되지만 타 개발자가 봤을 때 직관적인게 좋음
- 스프링 데이터 JPA가 인식해서 스프링 빈으로 등록

## 만약 Impl 대신 다른 이름으로 쓰고 싶다면?

### xml 설정

```java
 <repositories base-package="study.datajpa.repository" 
												repository-impl-postfix="Impl" />
```

### JavaConfig 설정

```java
@EnableJpaRepositories(basePackages = "study.datajpa.repository",
                       repositoryImplementationPostfix = "Impl")
```

실무에서는 주로 QueryDSL이나 SpringJdbcTemplate을 함께 사용할 때 사용자 정의 리포지토리 기능을 자주 사용합니다. 항상 사용자 정의 리포지토리가 필요한 것은 아닙니다. 그냥 임의의 리포지토리를 만들어도 됩니다. 예를들어 MemberQueryRepository를 인터페이스가 아닌 클래스로 만들고 스프링 빈으로 등록해서 그냥 직접 사용해도 됩니다. 물론 이 경우 스프링 데이터 JPA와는 아무런 관계 없이 별도로 동작하게 됩니다.

# Auditing

- 엔티티를 생성, 변경할 때 변경한 사람과 시간을 추적하고 싶으면?
    - 등록일
    - 수정일
    - 등록자
    - 수정자

## 순수 JPA 사용

등록일, 수정일 적용

```java
@MappedSuperclass
@Getter
public class JpaBaseEntity {

	@Column(updatable = false)
	private LocalDateTime createDate;
	private LocalDateTime updateDate;

	@PrePersist
	public void prePersist() {
		LocalDateTime now = LocalDateTime.now();
		createDate = now;
		updateDate = now;
	}

	@PreUpdate
	public void preUpdate() {
		updateDate = LocalDateTime.now();
	}

}
```

```java
public class Member extends JpaBaseEntity {
	...
}
```

## 스프링 데이터 JPA 사용

### 설정

`@EnableJpaAuditing` ⇒ 스프링 부트 설정 클래스에 적용

`@EntityListerners(AuditingEntityListener.class)` ⇒ 엔티티에 적용

### 스프링 데이터 Auditing 적용 - 등록일, 수정일

```java
@EntityListeners(AuditingEntityListener.class)
@MappedSuperclass
@Getter
public class BaseEntity {

	@CreatedDate
	@Column(updatable = false)
	private LocalDateTime createData;

	@LastModifiedDate
	private LocalDateTime lastModifiedDate;

}
```

### 스프링 데이터 Auditing 적용 - 등록자, 수정자

```java
@EntityListeners(AuditingEntityListener.class)
@MappedSuperclass
@Getter
public class BaseEntity {

	@CreatedDate
	@Column(updatable = false)
	private LocalDateTime createData;

	@LastModifiedDate
	private LocalDateTime lastModifiedDate;
	
	@CreatedBy
	@Column(updatable = false)
	private String createBy;
	
	@LastModifiedBy
	private String lastModifiedBy;

}
```

등록자, 수정자 처리 빈 등록

```java
@EnableJpaAuditing
@SpringBootApplication
public class DataJpaApplication {

	public static void main(String[] args) {
		SpringApplication.run(DataJpaApplication.class, args);
	}

	@Bean
	public AuditorAware<String> auditorProvider() {
		return () -> Optional.of(UUID.randomUUID().toString()); // 실제 사용값으로 변경
	}

}
```

예제에서는 UUID의 랜덤 값을 넣지만 실무에서는 세션 정보나, 스프링 시큐리티 로그인 정보를 넣으면 됩니다.

참고로 저장시점에 등록일, 등록자는 물론이고, 수정일, 수정자도 같은 데이터가 저장됩니다. 데이터가 중복 저장되는 것 같지만, 이렇게 해두면 변경 컬럼만 확인해도 마지막에 업데이트한 유저를 확인 할 수 있으므로 유지보수 관점에서 편리해지며 이렇게 하지 않으면 변경 컬럼이 `null`일 때 등록 컬럼을 또 찾아야 하는 번거로운 과정이 발생합니다.

만약 저장시점에 저장데이터만 입력하고 싶다면 `@EnableJpaAuditing(modifyOnCreate = false)` 옵션을 사용하면 됩니다.

### 전체 적용

`@EntityListeners(AuditingEntityListener.class)`를 생략하고 스프링 데이터 JPA가 제공하는 이벤트를 **엔티티 전체에 적용**하려면 orm.xml에 다음과 같이 등록하면 됩니다.

```java
 <?xml version="1.0" encoding="UTF-8"?>
 <entity-mappings xmlns="http://xmlns.jcp.org/xml/ns/persistence/orm"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://xmlns.jcp.org/xml/ns/persistence/orm 
http://xmlns.jcp.org/xml/ns/persistence/orm_2_2.xsd"
 version="2.2">
 `
    <persistence-unit-metadata>
        <persistence-unit-defaults>
            <entity-listeners>
                <entity-listener 
class="org.springframework.data.jpa.domain.support.AuditingEntityListener"/>
            </entity-listeners>
        </persistence-unit-defaults>
    </persistence-unit-metadata>
</entity-mappings>
```

# Web 확장

## 도메인 클래스 컨버터

HTTP 파라미터로 넘어온 엔티티의 아이디로 엔티티 객체를 찾아 바인딩 해주는 기능입니다.

### 도메인 클래스 컨버터 사용 전

```java
@GetMapping("/members/{id}")
public String findMember(@PathVariable("id") Long id) {
	Member member = memberRepository.findById(id).get();
	return member.getUsername();
}
```

### 도메인 클래스 컨버터 사용 후

```java
@GetMapping("/members2/{id}")
public String findMember(@PathVariable("id") Member member) {
	return member.getUsername();
}
```

주의할 점은 도메인 클래스 컨버터로 엔티티를 파라미터로 받으면, 이 엔티티는 트랜잭션이 없는 범위에서 엔티티를 조회했으므로, 엔티티를 변경해도 DB에 반영되지 않으니 단순 조회용으로만 사용해야 합니다.

## 페이징과 정렬

### 페이징과 정렬 예제

```java
@GetMapping("/members")
public Page<Member> list(Pageable pageable) {
	Page<Member> page = memberRepository.findAll(pageable);
	return page;
}
```

파라미터로 `Pageable`객체를 받아서 사용할 수 있으며 `Pageable`은 인터페이스이기 때문에 실제로는 `org.springramework.data.domain.PageRequest`객체가 생성됩니다.

요청 파라미터는 아래와 같이 쓰입니다.

- 예) `/members?page=0&size=3&sort=id,desc&sort=username,desc`
- page: 현재 페이지 (0부터 시작)
- size: 한 페이지에 노출할 데이터 건수
- sort: 정렬 조건을 정의

### 기본값 설정

**글로벌 설정**

```java
 spring.data.web.pageable.default-page-size=20 # 기본 페이지 사이즈
 spring.data.web.pageable.max-page-size=2000 # 최대 페이지 사이즈
```

**개별 설정**

```java
@RequestMapping(value = "/members_page", method = RequestMethod.GET)
 public String list(@PageableDefault(size = 12, sort = "username", 
                     direction = Sort.Direction.DESC) Pageable pageable) {
    ...
 }
```

**접두사**

- 페이징 정보가 둘 이상일 경우 접두사로 구분
- `@Qualifier`에 접두사명 추가 “{접두사명}_xxx”
- 예제 : `/members?member_page=0&order_page=1`

```java
public String list(
  @Qualifier("member") Pageable memberPageable,
  @Qualifier("order") Pageable orderPageable, ...
```

### Page 내용을 DTO로 변환

엔티티를 그대로 API로 노출하면 다양한 문제가 발생할 수 있기 때문에 꼭 DTO로 변환해서 반환해야 합니다. Page 객체는 `map()`을 지원해서 내부 데이터를 변환하여 반환할 수 있습니다.

**Member DTO**

```java
@Data
public class MemberDto {

	private Long id;
	private String username;

	public MemberDto(Long id, String username, String teamName) {
		this.id = id;
		this.username = username;
	}
}
```

**`Page.map()` 사용**

```java
@GetMapping("/members")
public Page<MemberDto> list(Pageable pageable) {
	return memberRepository.findAll(pageable).map(MemberDto::new);
}
```

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/XjTuV