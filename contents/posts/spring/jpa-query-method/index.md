---
emoji: "🚀"
title: "쿼리 메소드 기능"
date: 2025-03-30 00:00:00
update: 2025-03-30 00:00:00
tags:
  - Spring
  - JPA
series: "스프링 데이터 JPA"
---

# **쿼리 메소드 기능 3가지**

- 메소드 이름으로 쿼리 생성
- 메소드 이름으로 JPA NamedQuery 호출
- `@Query` 어노테이션을 사용해서 리파지토리 인터페이스에 쿼리 직접 정의

## 메소드 이름으로 쿼리 생성

메소드 이름으로 쿼리 생성은 말 그대로 이름을 분석해서 JPQL 쿼리를 실행하는 기능입니다.

### **순수 JPA 리포지토리**

```java
public List<Member> findByUsernameAndAgeGreaterThan(String username, int age) {
		return em.createQuery("select m from Member m where m.username = :username and m.age > :age")
			.setParameter("username", username)
			.setParameter("age", age)
			.getResultList();
	}
```

### **순수 JPA 테스트 코드**

```java
@Test
public void findByUsernameAndAgeGreaterThan() {
	Member m1 = new Member("AAA", 10);
	Member m2 = new Member("AAA", 20);
	memberJpaRepository.save(m1);
	memberJpaRepository.save(m2);

	List<Member> result = memberJpaRepository.findByUsernameAndAgeGreaterThan("AAA", 15);

	assertThat(result.get(0).getUsername()).isEqualTo("AAA");
	assertThat(result.get(0).getAge()).isEqualTo(20);
	assertThat(result.size()).isEqualTo(1);
}
```

### 스프링 데이터 JPA

```java
public interface MemberRepository extends JpaRepository<Member, Long> {
	List<Member> findByUsernameAndAgeGreaterThan(String username, int age);
}
```

- 스프링 데이터 JPA는 메소드 이름을 분석해서 JPQL을 생성하고 실행

`※쿼리 메소드 필터 조건 : [Spring Data JPA :: Spring Data JPA](https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html)`

### 스프링 데이터 JPA가 제공하는 쿼리 메소드 기능

- 조회 : find…By, read…By, query…By, get…By,
    - https://docs.spring.io/spring-data/jpa/reference/repositories/query-keywords-reference.html
    - findHelloBy 처럼 …에 식별하기 위한 내용(설명)이 들어갈 수 있음
- COUNT: count..By 반환타입 `long`
- EXISTS: exits…By 반환타입 `boolean`
- 삭제: delete…By 반환타입 `long`
- DISTINCT: findDistinct, findMemberDistinctBy
- LIMIT: findFirst3, findFirst, findTop, findTop3

이 기능은 엔티티의 필드명이 변견되면 인터페이스에 정의한 메서드 이름도 꼭 함께 변경해야 합니다. 그렇지 않으면 애플리케이션을 시작하는 시점에 오류가 발생합니다.

이렇게 애플리케이션 **로딩 시점에 오류를 인지**할 수 있는 것이 스프링 데이터 JPA의 매우 큰 장점입니다.

## JPA NamedQuery

JPA의 NamedQuery를 호출할 수 있는 기능입니다.

### `@NamedQuery` 어노테이션으로 Named 쿼리 정의

```java
@Entity
@NamedQuery(
	name="Member.findByUsername",
	query="select m from Member m where m.username = :username"
)
public class Member {
	...
}
```

### JPA를 직접 사용해서 Named 쿼리 호출

**MemberJpaRepository**

```java
public List<Member> findByUsername(String username) {
	return em.createNamedQuery("Member.findByUsername", Member.class)
		.setParameter("username", username)
		.getResultList();
}
```

### 스프링 데이터 JPA로 NamedQuery 사용

### MemberRepository

```java
@Query(name = "Member.findByUsername")
List<Member> findByUsername(@Param("username") String username);
```

- `@Query`를 생략하고 메서드 이름만으로 Name 쿼리를 호출할 수 있음

### 스프링 데이터 JPA로 Named 쿼리 호출

### MemberRepository

```java
List<Member> findByUsername(@Param("username") String username);
```

- 스프링 데이터는 JPA는 선언한”도메인 클래스 + .(점) + 메서드 이름”으로 Named 쿼리를 찾아서 실행
- 만약 실행할 Named 쿼리가 없으면 메서드 이름으로 쿼리 생성 전략을 사용
- 필요하면 전략을 변경할 수 있지만 권장되는 방법은 아님
    - https://docs.spring.io/spring-data/jpa/reference/repositories/query-methods-details.html
- 실무에서는 Named Query를 직접 등록해서 사용하는 일은 드물고 `@Query`를 사용해 쿼리를 직접 정의만 함

## @Query, 리포지토리 메소드에 쿼리 정의하기

### 메서드에 JPQL 쿼리 작성

```java
@Query("select m from Member m where m.username = :username and m.age = :age")
List<Member> findByUser(@Param("username") String username, @Param("age") int age);
```

- `@org.springframework.data.jpa.repository.Query` 어노테이션을 사용
- 실행할 메서드에 정적 쿼리를 직접 작성하므로 이름 없는 Named 쿼리라 할 수 있음
- JPA Named 쿼리처럼 애플리케이션 실행 시점에 문법 오류를 발결한 수 있음(매우 큰 장점)
- 실무에서는 메소드 이름으로 쿼리 작성시 파라미터가 매우 지저분해지니 `@Query`기능을 자주 사용함

### @Query, 값, DTO 조회하기

### 단순히 값 하나를 조회

**MemberRepository**

```java
@Query("select m.username from Member m")
List<String> findUsernameList();
```

- JPA 값 타입(`@Embedded`)도 이 방식으로 조회가능

### DTO로 직접 조회

```java
@Query("select new stduy.datajpa.dto.MemberDto(m.id, m.username, t.name)" 
		+ " from Member m join m.team t")
List<MemberDto> findMemberDto();
```

### 파라미터 바인딩

- 위치 기반
- 이름 기반

```java
select m from Member m where m.username = ?0 // 위치 기반
select m from Member m where m.username = :name // 이름 기반
```

**컬렉션 파라미터 바인딩**

`Collection` 타입으로 in절 지원

```java
@Query("select m from Member m where m.username in :names")
List<Member> findByNames(@Param("names") Collection<String> names);
```

### 반환 타입

스프링 데이터 JPA는 유연한 반환 타입을 지원합니다.

```java
List<Member> findByUsername(String name); // 컬렉션
Member findByUsername(String name); // 단건
Optional<Member> findByUsername(String name); // 단건 Optional
```

**조회 결과가 많거나 없으면?**

- 컬렉션
    - 결과 없음: 빈 컬렉션 반환
- 단건 조회
    - 결과 없음: `null`반환
    - 결과가 2건 이상: `javax.persistence.NonUniqueResultException` 예외 발생

단건으로 지정한 메서드를 호출하면 스프링 데이터 JPA는 내부에서 JPQL의 `Query.getSingleResult()`메서드를 호출합니다. 이 메서드를 호출했을 때 조회 결과가 없으면 `javax.persistence.NoResultException`예외가 발생하는데 개발자 입장에서 다루기가 상당히 불편합니다. 스프링 데이터 JPA는 단건을 조회할 때 이 예외가 발생하면 예외를 무시하고 대신 `null`을 반환합니다.

### 순수 JPA 페이징과 정렬

- 검색 조건: 나이가 10살
- 정렬 조건: 이름으로 내림차순
- 페이징 조건: 첫 번째 페이지, 페이지당 보여줄 데이터는 3건

**JPA 페이징 리포지토리 코드**

```java
public List<Member> findByPage(int age, int offset, int limit) {
		return em.createQuery("select m from Member m where m.age = :age order by m.username desc")
			.setParameter("age", age)
			.setFirstResult(offset)
			.setMaxResults(limit)
			.getResultList();
	}

public long totalCount(int age) {
	return em.createQuery("select count(m) from Member m where m.age = :age", Long.class)
		.setParameter("age", age)
		.getSingleResult();
}
```

**JPA 페이징 테스트 코드**

```java
@Test
public void paging() throws Exception {
	// given
    memberJpaRepository.save(new Member("member1", 10));
    memberJpaRepository.save(new Member("member2", 10));
    memberJpaRepository.save(new Member("member3", 10));
    memberJpaRepository.save(new Member("member4", 10));
    memberJpaRepository.save(new Member("member5", 10));

	int age = 10;
	int offset = 0;
	int limit = 3;

    // when
	List<Member> members = memberJpaRepository.findByPage(age, offset, limit);
	long totalCount = memberJpaRepository.totalCount(age);

	// then
	assertThat(members.size()).isEqualTo(3);
	assertThat(totalCount).isEqualTo(5);
}
```

### 스프링 데이터 JPA 페이징과 정렬

**페이징과 정렬 파라미터**

- `org.springframework.data.domain.Sort`: 정렬기능
- `org.springframework.data.domain.Pageable`: 페이징 기능(내부에 `Sort`포함)

**특별한 반환 타입**

- `org.springframework.data.domain.Page`: 추가 count 쿼리 결과를 포함하는 페이징
- `org.springframework.data.domain.Slice`: 추가 count 쿼리 없이 다음 페이지만 확인 가능(내부적으로 limit + 1조회)
- `List`(자바 컬렉션): 추가 count 쿼리 없이 결과만 반환

**페이징과 정렬 사용 예제**

```java
Page<Member> findByUsername(String name, Pageable pageable);  //count 쿼리 사용
Slice<Member> findByUsername(String name, Pageable pageable); //count 쿼리 사용 안함
List<Member> findByUsername(String name, Pageable pageable);  //count 쿼리 사용 안함
List<Member> findByUsername(String name, Sort sort);
```

**위와 같은 조건으로 페이징과 정렬을 사용한 예제 코드**

- 검색 조건: 나이가 10살
- 정렬 조건: 이름으로 내림차순
- 페이징 조건: 첫 번째 페이지, 페이지당 보여줄 데이터는 3건

**Page 사용 예제 정의 코드**

```java
@Test
public void paging() throws Exception {
	// given
	memberRepository.save(new Member("member1", 10));
	memberRepository.save(new Member("member2", 10));
	memberRepository.save(new Member("member3", 10));
	memberRepository.save(new Member("member4", 10));
	memberRepository.save(new Member("member5", 10));

	int age = 10;
	PageRequest pageRequest = PageRequest.of(
		0, 3, Sort.by(Sort.Direction.DESC, "username")
	);

	// when
	Page<Member> page = memberRepository.findByAge(age, pageRequest);

	// then
	List<Member> content = page.getContent(); // 조회된 데이터
	assertThat(content.size()).isEqualTo(3); // 조호된 데이터 수
	assertThat(page.getTotalElements()).isEqualTo(5); // 전체 데이터 수
	assertThat(page.getNumber()).isEqualTo(0); // 페이지 번호
	assertThat(page.getTotalPages()).isEqualTo(2); // 전체 페이지 번호
	assertThat(page.isFirst()).isTrue(); // 첫 번째 항목인가?
	assertThat(page.hasNext()).isTrue(); // 다음 페이지가 있는가?
}
```

- 두 번째 파라미터로 받은 `Pageable`은 인터페이스다. 따라서 실제 사용할 때는 해당 인터페이스를 구현한 `org.springframework.data.domain.PageRequest`객체를 사용한다
- `PageRequest` 생성자의 첫 번째 파라미터에는 현재 페이지를, 두 번째 파라미터에는 조회할 데이터 수를 입력한다. 여기에 추가로 정렬 정보도 파라미터로 사용할 수 있다. **(페이지는 0부터 시작)**

Page 인터페이스

```java
public interface Page<T> extends Slice<T> {
    static <T> Page<T> empty() {
        return empty(Pageable.unpaged());
    }

    static <T> Page<T> empty(Pageable pageable) {
        return new PageImpl(Collections.emptyList(), pageable, 0L);
    }

    int getTotalPages();

    long getTotalElements();

    <U> Page<U> map(Function<? super T, ? extends U> converter);
}
```

Slice 인터페이스

```java
public interface Slice<T> extends Streamable<T> {
    int getNumber();

    int getSize();

    int getNumberOfElements();

    List<T> getContent();

    boolean hasContent();

    Sort getSort();

    boolean isFirst();

    boolean isLast();

    boolean hasNext();

    boolean hasPrevious();

    default Pageable getPageable() {
        return PageRequest.of(this.getNumber(), this.getSize(), this.getSort());
    }

    Pageable nextPageable();

    Pageable previousPageable();

    <U> Slice<U> map(Function<? super T, ? extends U> converter);

    default Pageable nextOrLastPageable() {
        return this.hasNext() ? this.nextPageable() : this.getPageable();
    }

    default Pageable previousOrFirstPageable() {
        return this.hasPrevious() ? this.previousPageable() : this.getPageable();
    }
}
```

**count 쿼리를 다음과 같이 분리 가능**

```java
@Query(value = "select m from Member m",
			countQuery = "select count(m.username) from Member m")
Page<Member> findMemberAllCountBy(Pageable pageable);
```

**`※Count 쿼리 분리는 실무에서 복잡한 sql에서 사용`**

**Top, First 사용 참고**

https://docs.spring.io/spring-data/jpa/reference/repositories/query-methods-details.html#repositories.special-parameters

**페이지를 유지하면서 엔티티를 DTO로 변환**

```java
Page<Member> page = memberRepository.findByAge(age, pageRequest);
Page<MemberDto> toMap = page.map(
	member -> new MemberDto(member.getId(), member.getUsername(), null)
);
```

### 벌크성 수정 쿼리

**JPA를 사용한 벌크성 수정 쿼리**

```java
public int bulkAgePlus(int age) {
	return em.createQuery("update Member m set m.age = m.age + 1"
			+ " where m.age >= :age")
		.setParameter("age", age)
		.executeUpdate();
}
```

**JPA를 사용한 벌크성 수정 쿼리 테스트**

```java
@Test
public void bulkUpdate() throws Exception {
    // given
	memberJpaRepository.save(new Member("member1", 10));
	memberJpaRepository.save(new Member("member2", 19));
	memberJpaRepository.save(new Member("member3", 20));
	memberJpaRepository.save(new Member("member4", 21));
	memberJpaRepository.save(new Member("member5", 40));

    // when
	int resultCount = memberJpaRepository.bulkAgePlus(20);

	// then
	assertThat(resultCount).isEqualTo(3);
}
```

**스프링 데이터 JPA를 사용한 벌크성 수정 쿼리**

```java
@Modifying
@Query("update Member m set m.age = m.age + 1 where m.age >= :age")
int bulkAgePlus(@Param("age") int age);
```

**스프링 데이터 JPA를 사용한 벌크성 수정 쿼리 테스트**

```java
@Test
public void bulkUpdate() throws Exception {
	// given
	memberRepository.save(new Member("member1", 10));
	memberRepository.save(new Member("member2", 19));
	memberRepository.save(new Member("member3", 20));
	memberRepository.save(new Member("member4", 21));
	memberRepository.save(new Member("member5", 40));

	// when
	int resultCount = memberRepository.bulkAgePlus(20);

	// then
	assertThat(resultCount).isEqualTo(3);
}
```

- 벌크성 수정, 삭제 쿼리는 `@Modifying` 어노테이션을 사용
    - 사용하지 않으면 예외 발생
- 벌크성 쿼리를 실행하고 나서 영속성 컨텍스트 초기화: `@Modifying(clearAutomatically = true)`

  (이 옵션 기본값은 `false`)

    - 이 옵션 없이 회원을 `findById`로 다시 조회하면 영속성 컨텍스트에 과거 값이 남아서 문제가 될 수 있으니 다시 조회해야 한다면 꼭 영속성 컨텍스트를 초기화 해야함

벌크 연산은 영속성 컨텍스트를 무시하고 실행하기 때문에, 영속성 컨텍스트에 있는 엔티티의 상태와 DB에 엔티티 상태가 달라질 수 있습니다. 따라서 권장하는 방법은 다음과 같습니다.

1. 영속성 컨텍스트에 엔티티가 없는 상태에서 벌크 연산을 먼저 실행한다.
2. 부득이하게 영속성 컨텍스트에 엔티티가 있으면 벌크 연산 직후 영속성 컨텍스트를 초기화 한다.

### @EntityGraph

연관된 엔티티들을 SQL 한 번에 조회하는 방법입니다. 예를 들어 member ⇒ team은 지연로딩 관계로 member의 team은 프록시 객체기에 데이터를 조회할 때 마다 N+1 문제가 발생하게 됩니다.

```java
@Test
public void findMemberLazy() throws Exception {
	//given
	//member1 -> teamA
	//member2 -> teamB
	Team teamA = new Team("teamA");
	Team teamB = new Team("teamB");
	teamRepository.save(teamA);
	teamRepository.save(teamB);
	memberRepository.save(new Member("member1", 10, teamA));
	memberRepository.save(new Member("member2", 20, teamB));
	em.flush();
	em.clear();
	//when
	List<Member> members = memberRepository.findAll("member1");
	//then
	for (Member member : members) {
		member.getTeam().getName();
		System.out.println("member = " + member.getTeam().getClass());
	}
}
```

이 때, N+1 문제를 해결하기 위해 연관된 엔티티를 한 번에 조회하려면 페치 조인을 사용해야 합니다.

```java
@Query("select m from Member m left join fetch m.team")
List<Member> findMemberFetchJoin();
```

여기서 엔티티 그래프 기능을 사용하면 별도의 JPQL을 사용할 필요 없이 원하는대로 페치 조인을 사용할 수 있습니다.

**EntityGraph**

```java
@Override
@EntityGraph(attributePaths = {"team"})
List<Member> findAll();

@EntityGraph(attributePaths = {"team"})
@Query("select m from Member m")
List<Member> findMemberEntityGraph();

@EntityGraph(attributePaths = {"team"})
List<Member> findByUsername(String username);
```

엔티티 그래프는 페치 조인의 간편 버전으로 복잡하지 않은 쿼리라면 `@EntityGraph`어노테이션을 통해 간단히 N+1 문제를 해결할 수도 있으며 엔티티 클래스 자체에 엔티티 그래프를 사용하는 `NamedEntityGrpah`도 있습니다.

**NamedEntityGraph**

```java
@NamedQuery(
	name="Member.findByUsername",
	query="select m from Member m where m.username = :username"
)
@NamedEntityGraph(name = "Member.all", attributeNodes = @NamedAttributeNode("team"))
public class Member {
```

```java
// @EntityGraph(attributePaths = {"team"})
@EntityGraph("Member.all")
List<Member> findEntityGraphByUsername(@Param("username")String username);
```

### JPA Hint

JPA 쿼리 힌트는 SQL 힌트가 아닌 JPQ 구현체에게 제공하는 힌트입니다.

**쿼리 힌트 사용**

```java
@QueryHints(value = @QueryHint(name = "org.hibernate.readOnly", value = "true"))
Member findReadOnlyByUsername(String username);
```

`※ 엔티티가 변경 되었음에도 update 쿼리는 발생하지 않음`

**페이징용 쿼리 힌트**

```java
@QueryHints(value = { @QueryHint(name = "org.hibernate.readOnly", value = "true")}, forCounting = true)
Page<Member> findByUsername(String name, Pageable pageable);
```

JPA의 더티 체킹은 어쨋든 “변경”에 대한 감지를 하는 것이기 때문에 JPA 내부적으로 최적화를 하더라도 두 개의 객체를 관리하고 있기 떄문에 비용이 발생함. 만약 “나는 변경감지(update) 없이 100% 조회용으로만 쓸거야!” 라고 한다면 쿼리 힌트를 통해 해결할 수 있음

다만 실무에서는 readOnly로 최적화 하는 경우는 정~~~말 트래픽이 몰리는 중요한 API 한 두개지 90% 이상의 경우는 복잡한 DB 쿼리로 인해 발생함. 데이터 캐싱을 고려하기 “직전” 약간의 성능 향상을 위해 시도해볼만함

### Lock

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
List<Member> findLockByUsername(String name);
```

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/XjTuV