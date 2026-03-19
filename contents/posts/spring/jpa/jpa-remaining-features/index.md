---
emoji: "🚀"
title: "나머지 기능들"
date: 2025-04-02 00:00:00
update: 2025-04-02 00:00:00
tags:
  - Spring
  - JPA
series: "스프링 데이터 JPA"
---

앞으로 나올 기능들은 실무에서 쓰기에는 애매한 기능들이라 **나머지 기능들**이라 정하였으니 비교적 가볍게 들어도 되는 주제입니다.

# Specifications(명세)

책 도메인 주도 설계라는 책을 보면 Specification(명세)라는 개념을 소개합니다. 스프링 데이터 JPA는 JPA Criteria를 활용해서 이 개념을 사용할 수 있도록 지원하고 있습니다.

## 술어(predicate)

- 참 또는 거짓으로 평가
- AND OR 같은 연산자로 조합해서 다양한 검색조건을 쉽게 생성(컴포지트 패턴)
- 예) 검색 조건 하나하나
- 스프링 데이터 JPA는 `org.springframework.data.jpa.domain.Spcification`클래스로 정의

## 명세 기능 사용 방법

`JpaSpecificationExecutor` 인터페이스 상속

```java
public interface MemberRepository extends JpaRepository<Member, Long>, 
																						JpaSpecificationExecutor<Member> {
}
```

`JpaSpecificationExecutor` 인터페이스

```java
public interface JpaSpcificationExecutor<T> {
		Optional<T> findOne(@Nullable Specification<T> spec);
		List<T> findAll(Specification<T> spec);
		Page<T> findAll(Specification<T> spec, Pageable pageable);
		List<T> findAll(Specification<T> spec, Sort sort);
		long count(Specification<T> spec);
}
```

`Specification`을 파라미터로 받아서 검색 조건으로 사용

## 명세 사용 코드

```java
@Test
	public void specBasic() throws Exception {
	    // given
		Team teamA = new Team("teamA");
		em.persist(teamA);

		Member m1 = new Member("m1", 0, teamA);
		Member m2 = new Member("m2", 0, teamA);
		em.persist(m1);
		em.persist(m2);

		em.flush();
		em.clear();

		// when
		Specification<Member> spec = MemberSpec.username("m1").and(MemberSpec.teamName("teamA"));
		List<Member> result = memberRepository.findAll(spec);

		// then
		Assertions.assertThat(result.size()).isEqualTo(1);
	}
```

- `Specification`을 구현하면 명세들을 조립할 수 있음. `where()`, `and()`, `not()` 제공
- `findAll`을 보면 회원 이름 명세(`username`)와 팀 이름 명세 (`teamName`)를 `and`로 조합해서 검색 조건으로 사용

`MemberSpec` 명세 정의 코드

```java
public class MemberSpec {

	public static Specification<Member> teamName(final String teamName) {
		return (root, query, criteriaBuilder) -> {
			if (StringUtils.isEmpty(teamName)) {
				return null;
			}

			Join<Object, Team> t = root.join("team", JoinType.INNER); // 회원과 조인
			return criteriaBuilder.equal(t.get("name"), teamName);
		};
	}

	public static Specification<Member> username(final String username) {
		return (root, query, criteriaBuilder) ->
			criteriaBuilder.equal(root.get("username"), username);
	}
}
```

- 명세를 정의하려면 `Specification` 인터페이스를 구현
- 명세를 정의할 때는 `toPredicate(...)` 메서드만 구현하면 되는데 JPA Criteria의 `Root` , `CriteriaQuery`, `CriteriaBuilder` 클래스를 파라미터 제공

이전 JPA 강의에서 설명했듯 알아 보기가 힘들기 때문에 criteria는 실무에서 거의 쓰지 않기에 QueryDSL을 사용해야 합니다.

# Query By Example

```java
@Test
	public void queryByExample() throws Exception {
	    // given
		Team teamA = new Team("teamA");
		em.persist(teamA);

		Member m1 = new Member("m1", 0, teamA);
		Member m2 = new Member("m2", 0, teamA);
		em.persist(m1);
		em.persist(m2);

		em.flush();
		em.clear();

		// when

	    // then
		// Probe
		Member member = new Member("m1");

		ExampleMatcher matcher = ExampleMatcher.matching()
			.withIgnorePaths("age");

		Example<Member> example = Example.of(member, matcher);

		memberRepository.findAll(example);

		List<Member> result = memberRepository.findAll(example);

		assertThat(result.get(0).getUsername()).isEqualTo("m1");
	}
```

- Probe : 필드에 데이터가 있는 실제 도메인 객체
- ExampleMathcer: 특정 필드를 일치시키는 상세한 정보 제공, 재사용 가능
- Example: Probe와 ExampleMatcher로 구성, 쿼리를 생성하는데 사용

**장점**

- 동적 쿼리를 편리하게 처리
- 도메인 객체를 그대로 사용
- 데이터 저장소를 RDB에서 NOSQL로 변경해도 코드 변경이 없게 추상화 되어 있음
- 스프링 데이터 JPA `JpaRepository` 인터페이스에 이미 포함

**단점**

- 조인은 가능하지만 내부 조인(INNER JOIN)만 가능함 외부 조인(LEFT JOIN) 안됨
- 다음과 같은 중첩 제약조건 안됨
    - `firstname = ?0 or (fristername = ?! and lastname = ?@)`
- 매칭 조건이 매우 단순함
    - 문자는 `starts/contains/ends/regex`
    - 다른 속성은 정확한 매칭(`=`)만 지원

**정리**

- 실무에서 사용하기에는 매칭 조건이 너무 단순하고, LEFT 조인이 안됨
- 실무에서는 QueryDSL을 사용하자

# Projections

엔티티 대신에 DTO를 편리하게 조회할 때 사용하는 기능으로 전체 엔티티가 아니라 특정 필드만 조회하고 싶을 때 사용합니다. 편하게 select를 통해 찝어서 가져온다 생각하면 됩니다.

## 인터페이스 기반 Proejction

```java
public interface UsernameOnly {
	String getUsername();
}
```

- 조회할 엔티티의 필드를 getter 형식으로 지정하면 해당 필드만 선택해서 조회함(Projection)

```java
// Return Type으로 해당 DTO 지정
List<UsernameOnly> findProjectionsByUsername(@Param("username") String username);
```

- 메서드 이름은 자유, 반환 타입으로 인지

**ClosedProjection 테스트**

```java
@Test
public void projections() throws Exception {
    // given
	Team teamA = new Team("teamA");
	em.persist(teamA);

	Member m1 = new Member("m1", 0, teamA);
	Member m2 = new Member("m2", 0, teamA);
	em.persist(m1);
	em.persist(m2);

	em.flush();
	em.clear();

    // when
	List<UsernameOnly> result = memberRepository.findProjectionsByUsername("m1");

	for (UsernameOnly usernameOnly: result) {
		System.out.println("usernameOnly = " + usernameOnly);
	}

	// then
}
```

스프링의 SpEL 문법을 활용하여 쿼리를 사용할 수도 있습니다.

```java
@Value("#{target.username + ' ' + target.age}")
String getUsername();
```

단, 이렇게 SpEL 문법을 사용하면, DB에서 엔티티 필드를 다 조회해온 다음에 계산하기 때문에 JPQL SELECT 최적화는 되지 않습니다.

## 클래스 기반 Proejction

```java
public class UsernameOnlyDto {

	private final String username;

	public UsernameOnlyDto(String username) {
		this.username = username;
	}

	public String getUsername() {
		return username;
	}
}
```

인터페이스가 아닌 구체적인 DTO 형식으로도 Proejction을 사용할 수 있습니다. JPA는 **생성자의 파라미터 이름**을 기준으로 매칭하게 됩니다.

## 동적 Projections

다음과 같이 Generic type을 주면 동적으로 프로젝션 데이터 변경도 가능합니다.

```java
<T> List<T> findProjectionsByUsername(@Param("username") String username, Class<T> type);
```

## 중첩 구조 처리

```java
public interface NestedClosedProjections {

	String getUsername();
	TeamInfo getTeam();

	interface TeamInfo {
		String getName();
	}
}
```

**주의사항**

- 프로젝션 대상이 root 엔티티면, JPQL SELECT절로 최적화 가능
- 프로젝션 대상이 ROOT가 아니면
    - LEFT OUTER JOIN 처리
    - 모든 필드를 SELECT해서 엔티티로 조회한 다음에 계산

**정리**

- 프로젝션 대상이 root 엔티티면 유용하다.
- 프로젝션 대상이 root 엔티티를 넘어가면 JPQL SELECT 최적화가 안된다
- 실무의 복잡한 쿼리를 해결하기에는 한계가 있다.
- 실무에서는 단순할 때만 사용하고, 조금만 복잡해지면 QueryDSL을 사용하자

# JPA 네이티브 SQL 지원

**스프링 데이터 JPA 기반 네이티브 쿼리**

- 페이징 지원
- 반환 타입
    - Object[]
    - Tuple
    - DTO(스프링 데이터 인터페이스 Proejctions 지원)
- 제약
    - Sort 파라미터를 통한 정렬이 정상 동작하지 않을 수 있음(믿지 말고 직접 처리)
    - JPQL처럼 애플레키에션 로딩 시점에 문법 확인 불가
    - 동적 쿼리 불가

```java
@Query(value = "select * from member where username = ?", nativeQuery = true)
Member findByNativeQuery(String username);
```

- JPQL은 위치 기반 파라미터를 1부터 시작하지만 SQL은 0부터 시작
- 네이티브 SQL을 엔티티가 아닌 DTO로 변환을 하려면
    - DTO 대신 JPA TUPLE 조회
    - DTO 대신 MAP 조회
    - @SqlResultSetMapping ⇒ 복잡
    - Hibernate ResultTransformer를 사용해야 함 ⇒ 복잡
    - 네이티브 SQL을 DTO로 조회할 때는 JdbcTemplate or mybatis 권장

### Projctions 활용

예) 스프링 데이터 JPA 네이티브 쿼리 + 인터페이스 기반 Proejctions 활용

```java
@Query(value = "select m.member_id as id, m.username, t.name as teamName " 
		+ "from member m left join team t",
		countQuery = "select count(*) from member",
		nativeQuery = true)
	Page<MemberProjection> findByNativeProjection(Pageable pageable);
```

### 동적 네이티브 쿼리

- 하이버네이트를 직접 활용
- 스프링 JdbcTemplate, myBatis, jooq같은 외부 라이브러리 사용

예) 하이버네이트 기능 사용

```java
String sql = "select m.username as username from member m";
List<MemberDto> result = em.createNativeQuery(sql)
      .setFirstResult(0)
      .setMaxResults(10)
      .unwrap(NativeQuery.class)
      .addScalar("username")
      .setResultTransformer(Transformers.aliasToBean(MemberDto.class))
      .getResultList();
}
```

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/XjTuV