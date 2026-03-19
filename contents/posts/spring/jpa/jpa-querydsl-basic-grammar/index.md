---
emoji: "🚀"
title: "기본 문법"
date: 2025-05-19 00:00:00
update: 2025-05-19 00:00:00
tags:
  - Spring
  - JPA
series: "Querydsl"
---

# JPQL VS Querydsl

## 테스트 기본 코드

```java
@SpringBootTest
@Transactional
public class QuerydslBasicTest {

	@PersistenceContext
	EntityManager em;

	@BeforeEach
	public void before() {
		Team teamA = new Team("teamA");
		Team teamB = new Team("teamB");
		em.persist(teamA);
		em.persist(teamB);
		Member member1 = new Member("member1", 10, teamA);
		Member member2 = new Member("member2", 20, teamA);
		Member member3 = new Member("member3", 30, teamB);
		Member member4 = new Member("member4", 40, teamB);
		em.persist(member1);
		em.persist(member2);
		em.persist(member3);
		em.persist(member4);
	}
```

## JPQL VS Querydsl

```java
@Test
public void startJPQL() throws Exception {
    // given
	Member findMember = em.createQuery("select m from Member m where m.username = :username", Member.class)
		.setParameter("username", "member1")
		.getSingleResult();

	// when

    // then
	assertThat(findMember.getUsername()).isEqualTo("member1");
}

@Test
public void startQuerydsl() throws Exception {
    // given
	JPAQueryFactory queryFactory = new JPAQueryFactory(em);
	QMember m = new QMember("M");

	// when
	Member findMember = queryFactory
		.select(m)
		.from(m)
		.where(m.username.eq("member1"))
		.fetchOne();

    // then
	assertThat(findMember.getUsername()).isEqualTo("member1");
}
```

- `EntityManager`로 `JPAQueryFactory` 생성
- querydsl은 JPQL 빌더
- JPQL: 문자(실행 시점 오류), Querydsl: 코드(컴파일 시점 오류)
- JPQL: 파라미터 바인딩 직접, Querydsl: 파라미터 바인딩 자동 처리

## JPAQueryFactory를 필드로 사용

```java
@SpringBootTest
@Transactional
public class QuerydslBasicTest {

	@PersistenceContext
	EntityManager em;

	JPAQueryFactory queryFactory;

	@BeforeEach
	public void before() {
		...
	}

	@Test
	public void startJPQL() throws Exception {
	  ...
	}

	@Test
	public void startQuerydsl() throws Exception {
    // given
		queryFactory = new JPAQueryFactory(em);
		QMember m = new QMember("M");

		// when
		Member findMember = queryFactory
			.select(m)
			.from(m)
			.where(m.username.eq("member1"))
			.fetchOne();

    // then
		assertThat(findMember.getUsername()).isEqualTo("member1");

	}
}
```

JPQQueryFactory는 필드로 제공시 동시성에 대해 고민할 수 있겠지만 생성할 때 제공되는 EntityManger(em)에 달려있습니다.  스프링은 여러 쓰레드에서 동시에 같은 EntityManager에 접근해도, 트랜잭션 마다 별도의 영속성 컨텍스트를 제공하기 때문에, 동시성 문제는 발생하지 않습니다.

# 기본 Q-Type 활용

## Q클래스 인스턴스를 사용하는 2가지 방법

```java
QMember qMember = new QMember("m");
QMember qMember = QMember.member;
```

QMember의 구현체를 따라가보면 querydsl이 Q-Class 내 미리 만들어둔 member class가 있는걸 확인할 수 있습니다.

![image.png](attachment:701d6267-a43a-4fec-871c-7168fffe6063:image.png)

## 기본 인스턴스를 static import와 함께 사용

```java
import static stduy.querydsl.entity.QMember.*;

@Test
public void startQuerydsl() throws Exception {
  // given
	// when
	Member findMember = queryFactory
		.select(member)
		.from(member)
		.where(member.username.eq("member1"))
		.fetchOne();

    // then
	assertThat(findMember.getUsername()).isEqualTo("member1");
}
```

위 캡쳐와 같이 기본 인스턴스로 member1이 지정되어 있으니 같은 테이블을 조인해야 하는 경우가 아니라면 깔끔하게 기본 인스턴스를 사용하는 것을 권장합니다.

# 검색 조건 쿼리

## 기본 검색 쿼리

```java
@Test
public void search() throws Exception {
  // given
	Member findMember = queryFactory
		.selectFrom(member)
		.where(member.username.eq("member1")
			.and(member.age.eq(10)))
		.fetchOne();

	// when

  // then
	assertThat(findMember.getUsername()).isEqualTo("member1");
}
```

검색 조건은 `.and()`, `.or()`를 메서드 체인으로 연결할 수 있습니다.

## JPQL이 제공하는 모든 검색 조건 제공

```java
member.username.eq("member1") // username = 'member1'
member.username.ne("member1") //username != 'member1'
member.username.eq("member1").not() // username != 'member1'
member.username.isNotNull() //이름이 is not null
member.age.in(10, 20) // age in (10,20)
member.age.notIn(10, 20) // age not in (10, 20)
member.age.between(10,30) //between 10, 30
member.age.goe(30) // age >= 30
member.age.gt(30) // age > 30
member.age.loe(30) // age <= 30
member.age.lt(30) // age < 30
member.username.like("member%") //like 검색
member.username.contains("member") // like ‘%member%’ 검색 
member.username.startsWith("member") //like ‘member%’ 검색
...
```

## AND 조건을 파라미터로 처리

```java
@Test
public void searchAndParam() throws Exception {
	// given
	Member findMember = queryFactory
		.selectFrom(member)
		.where(
			member.username.eq("member1"),
			member.age.eq(10)
		)
		.fetchOne();

	// when

	// then
	assertThat(findMember.getUsername()).isEqualTo("member1");
}
```

`where()`에 파라미터로 검색 조건을 추가하면 자동으로 `AND` 조건이 추가됩니다. 이 경우 `null` 값은 무시되며 이후 메서드 추출을 활용해 **동적 쿼리를 깔끔하게** 만들 수 있게됩니다.

## 결과 조회

- `fetch()`: 리스트 조회, 데이터 없으면 빈 리스트 반환
- `fetchOne()`: 단 건 조회
    - 결과가 없으면 : `null`
    - 결과가 둘 이상이면 : `com.querydsl.core.NonUniqueResultException`
- `fetchFirst()`: `limit(1).fetchOne()`
- `fetchResults()`: 페이징 정보 포함, total count 쿼리 추가 실행
- `fetchCount()`: count 쿼리로 변경해서 count 수 조회

## 정렬

```java
/**
 * 회원 정렬 순서
 * 1. 회원 나이 내림차순(desc)
 * 2. 회원 이름 올림차순(asc)
 * 단 2에서 회원 이름이 없으면 마지막에 출력(nulls last)
 */
@Test
public void sort() throws Exception {
    // given
	em.persist(new Member(null, 100));
	em.persist(new Member("member5", 100));
	em.persist(new Member("member6", 100));

	List<Member> result = queryFactory
		.selectFrom(member)
		.where(member.age.eq(100))
		.orderBy(member.age.desc(), member.username.asc().nullsLast())
		.fetch();

	// when
	Member member5 = result.get(0);
	Member member6 = result.get(1);
	Member memberNull = result.get(2);

	// then
	assertThat(member5.getUsername()).isEqualTo("member5");
	assertThat(member6.getUsername()).isEqualTo("member6");
	assertThat(memberNull.getUsername()).isNull();
}
```

## 페이징

### 조회 건수 제한

```java
@Test
public void paging1() throws Exception {
    // given
	List<Member> result = queryFactory
		.selectFrom(member)
		.orderBy(member.username.desc())
		.offset(1)
		.limit(2)
		.fetch();

	// when

    // then
	assertThat(result.size()).isEqualTo(2);
}
```

### 전체 조회 수 필요시

```java
@Test
public void paging2() throws Exception {
	// given
	QueryResults<Member> results = queryFactory
		.selectFrom(member)
		.orderBy(member.username.desc())
		.offset(1)
		.limit(2)
		.fetchResults();

	// when

	// then
	assertThat(results.getTotal()).isEqualTo(4);
	assertThat(results.getLimit()).isEqualTo(2);
	assertThat(results.getOffset()).isEqualTo(1);
	assertThat(results.getResults()).size().isEqualTo(2);
}
```

실무에서 페이징 쿼리를 작성할 때, 데이터를 조회하는 쿼리는 여러 테이블을 조인해야 하지만, count 쿼리는 조인이 필요 없는 경우가 있습니다. 그런데 이렇게 자동화된 count 쿼리는 원본 쿼리와 같이 모두 조인을 해버리기 때문에 성능이 안나올 수 있습니다. count 쿼리에 조인이 필요없는 성능 최적화가 필요하다면 count 전용 쿼리를 별도로 작성해야 합니다.

## 집합

### 집합 함수

```java
@Test
public void aggregation() throws Exception {
	List<Tuple> result = queryFactory
		.select(
			member.count(),
			member.age.sum(),
			member.age.avg(),
			member.age.max(),
			member.age.min()
		)
		.from(member)
		.fetch();

	Tuple tuple = result.get(0);

	assertThat(tuple.get(member.count())).isEqualTo(4);
	assertThat(tuple.get(member.age.sum())).isEqualTo(100);
	assertThat(tuple.get(member.age.avg())).isEqualTo(25);
	assertThat(tuple.get(member.age.max())).isEqualTo(40);
	assertThat(tuple.get(member.age.min())).isEqualTo(10);
}
```

### GroupBy 사용

```java
/**
 * 팀의 이름과 각 팀의 평균 연령
 */
@Test
public void group() throws Exception {
	List<Tuple> result = queryFactory
		.select(team.name, member.age.avg())
		.from(member)
		.join(member.team, team)
		.groupBy(team.name)
		.fetch();

	Tuple teamA = result.get(0);
	Tuple teamB = result.get(1);

	assertThat(teamA.get(team.name)).isEqualTo("teamA");
	assertThat(teamA.get(member.age.avg())).isEqualTo(15);

	assertThat(teamB.get(team.name)).isEqualTo("teamB");
	assertThat(teamB.get(member.age.avg())).isEqualTo(35);
}
```

### groupBy(), having() 예시

```java
…
.groupBy(item.price)
.having(item.price.gt(1000))
…
```

# 조인 - 기본 조인

## 기본조인

조인의 기본 문법은 첫 번째 파라미터에 조인 대상을 지정하고, 두 번째 파라미터에 별칭(alias)으로 사용할 Q 타입을 지정하며 됩니다.

```java
join(조인 대상, 별칭으로 사용할 Q타입)
```

### 기본조인

```java
/**
 * 팀 A에 소속된 모든 회원
 */
@Test
public void join() throws Exception {
	List<Member> result = queryFactory
		.selectFrom(member)
		.join(member.team, team)
		.where(team.name.eq("teamA"))
		.fetch();

	assertThat(result)
		.extracting("username")
		.containsExactly("member1", "member2");
}
```

- `join()`, `innerJoin()`: 내부 조인(innerJoin)
- `leftJoin()` : left 외부 조인(left outer join)
- `rightJoin()` : right 외부 조인(right outer join)
- JPQL의 `on`과 성능 최적화를 위한 `fetch` 조인 제공 ⇒ 다음 on 절에서 설명

### 세타 조인

연관관계가 없는 필드로 조인

```java
/**
 * 세타 조인
 * 회원의 이름이 팀 이름과 같은 회원 조회
 */
@Test
public void theta_join() throws Exception {
	em.persist(new Member("teamA"));
	em.persist(new Member("teamB"));

	List<Member> result = queryFactory
		.selectFrom(member)
		.from(member, team)
		.where(member.username.eq(team.name))
		.fetch();

	assertThat(result)
		.extracting("username")
		.containsExactly("teamA", "teamB");
}
```

- from 절에 여러 엔티티를 선택해서 세타 조인
- 외부 조인 불가능 ⇒ 다음에 설명할 조인 on을 사용하면 외부 조인 가능

## 조인 - on절

ON절을 활용한 조인이며 조인 대상을 필터링 하거나 연관관계 없는 엔티티를 외부 조인합니다.

### 1. 조인 대상 필터링

예) 회원과 팀을 조인하면서, 팀 이름이 teamA인 팀만 조인, 회원은 모두 조회

```java
/**
 * 회원과 팀을 조인하면서, 팀 이름이 teamA인 팀만 조인, 회원은 모두 조회
 * JPQL : SELECT m, t FROM Member m LEFT JOIN m.team t WHERE t.name = 'teamA'
 * SQL : SELECT m.*, t.* FROM member m LEFT JOIN team t ON t.team_id = m.team_id WHERE t.name = 'teamA'
 */
@Test
public void join_on_filtering() throws Exception {
	List<Tuple> result = queryFactory
		.select(member, team)
		.from(member)
		.leftJoin(member.team, team).on(team.name.eq("teamA"))
		.fetch();

	for (Tuple tuple : result) {
		System.out.println("tuple = " + tuple);
	}
}
```

on 절을 활용해 조인 대상을 필터링 할 때, 외부조인이 아니라 내부조인(inner join)을 사용하면, where 절에서 필터링 하는 것과 기능이 동일합니다. 따라서 on 절을 활용한 조인 대상 필터링을 사용할 때, 내부조인이면 익숙한 where 절로 해결하고, 정말 외부조인이 필요할 경우에만 이 기능을 사용하는 것을 추천드립니다.

### 2. 연관관계 없는 엔티티 외부 조인

예) 회원의 이름과 팀의 이름이 같은 대상 **외부 조인**

```java
/**
 * 연관관계 없는 엔티티 외부 조인
 * 회원의 이름이 팀 이름과 같은 대상 외부 조인
 */
@Test
public void join_on_no_relation() throws Exception {
	em.persist(new Member("teamA"));
	em.persist(new Member("teamB"));

	List<Tuple> result = queryFactory
		.select(member, team)
		.from(member)
		.leftJoin(team).on(member.username.eq(team.name))
		.fetch();

	for (Tuple tuple : result) {
		System.out.println("tuple = " + tuple);
	}
}
```

- 하이버네이트 5.1부터 `on`을 사용해서 서로 관계가 없는 필드로 외부 조인하는 기능이 추가되었으며 내부 조인도 가능함.
- 주의! 문법을 잘 봐야 한다. **leftJoin()** 부분에 일반 조인과 다르게 엔티티 하나만 들어간다.
    - 일반조인 : `leftJoin(member.team, team)`
    - on조인 : `from(member).leftJoin(team).on(xxx)`

## 조인 - 페치 조인

페치 조인은 SQL에서 제공하는 기능은 아니며 SQL 조인을 활용해서 연관된 엔티티를 SQL 한번에 조회하는 기능입니다. 주로 성능 최적화에 사용하는 방법입니다.

### 페치 조인 미적용

지연로딩으로 Member, Team SQL 쿼리 각각 실행

```java
@PersistenceUnit
EntityManagerFactory emf;

@Test
public void fetchJoinNo() throws Exception {
	em.flush();
	em.clear();

	Member findMember = queryFactory
		.selectFrom(member)
		.where(member.username.eq("member1"))
		.fetchOne();

	boolean loaded = emf.getPersistenceUnitUtil().isLoaded(findMember.getTeam());
	assertThat(loaded).as("페치 조인 미적용").isFalse();
}
```

### 페치 조인 적용

즉시로딩으로 member, Team SQL 쿼리 조인으로 한번에 조회

```java
@Test
public void fetchJoinUse() throws Exception {
	em.flush();
	em.clear();

	Member findMember = queryFactory
		.selectFrom(member)
		.join(member.team, team).fetchJoin()
		.where(member.username.eq("member1"))
		.fetchOne();

	boolean loaded = emf.getPersistenceUnitUtil().isLoaded(findMember.getTeam());
	assertThat(loaded).as("페치 조인 적용").isTrue();
}
```

- `join(), leftJoin()`등 조인 기능 뒤에 `fetchJoin()`이라고 추가하면 됩니다.

## 서브 쿼리

`com.querydsl.jpa.JPAExpressions` 사용

### 서브 쿼리 eq 사용

```java
/**
 * 나이가 가장 많은 회원 조회
 */
@Test
public void subQuery() throws Exception {
	QMember memberSub = new QMember("memberSub");

	List<Member> result = queryFactory
		.selectFrom(member)
		.where(member.age.eq(
			JPAExpressions
				.select(memberSub.age.max())
				.from(memberSub)
		))
		.fetch();
	assertThat(result).extracting("age")
		.containsExactly(40);
}
```

### 서브쿼리 goe 사용

```java
/**
 * 나이가 평균 이상인 회원
 */
@Test
public void subQueryGoe() throws Exception {
	QMember memberSub = new QMember("memberSub");

	List<Member> result = queryFactory
		.selectFrom(member)
		.where(member.age.goe(
			JPAExpressions
				.select(memberSub.age.avg())
				.from(memberSub)
		))
		.fetch();
	assertThat(result).extracting("age")
		.containsExactly(30, 40);
}
```

### 서브쿼리 여러 건 처리 in 사용

```java
/**
 * 서브쿼리 여러 건 처리, in 사용
 */
@Test
public void subQueryIn() throws Exception {
	QMember memberSub = new QMember("memberSub");

	List<Member> result = queryFactory
		.selectFrom(member)
		.where(member.age.in(
			JPAExpressions
				.select(memberSub.age)
				.from(memberSub)
				.where(memberSub.age.gt(10))
		))
		.fetch();
	assertThat(result).extracting("age")
		.containsExactly(20, 30, 40);
}
```

### select절 서브쿼리

```java
/**
 * select절 subquery
 */
@Test
public void selectSubQuery() throws Exception {
	QMember memberSub = new QMember("memberSub");

	List<Tuple> result = queryFactory
		.select(member.username,
			JPAExpressions
				.select(memberSub.age.avg())
				.from(memberSub))
		.from(member)
		.fetch();

	for (Tuple tuple : result) {
		System.out.println("tuple = " + tuple);
	}
}
```

### from 절의 서브쿼리 한계

JPA JPQL 서크붜리의 한계점으로 from 절의 서브쿼리(인라인 뷰)는 지원하지 않기에 당연히 Querydsl도 지원하지 않습니다. 하이버네이트 구현체를 사용하면 select 절의 서브쿼리는 지원하며 Querydsl 역시 하이버네이트 구현체를 사용하면 select 절의 서브쿼리를 지원합니다.

### from 절의 서브쿼리 해결방안

1. 서브쿼리를 join으로 변경 (가능한 상황이 있고, 불가능한 상황이 있음)
2. 애플리케이션에서 쿼리를 2번 분리해서 실행
3. nativeSQL을 사용

## Case 문

**select, 조건절(where)에서 사용가능**

### 단순 조건

```java
@Test
public void basicCase() throws Exception {
	List<String> result = queryFactory
		.select(member.age
			.when(10).then("열살")
			.when(20).then("스무살")
			.otherwise("기타"))
		.from(member)
		.fetch();

	for (String s : result) {
		System.out.println("s = " + s);
	}
}
```

### 복잡한 조건

```java
@Test
public void complexCase() throws Exception {
	List<String> result = queryFactory
		.select(new CaseBuilder()
			.when(member.age.between(0, 20)).then("0~20살")
			.when(member.age.between(21, 30)).then("21살~30살")
			.otherwise("기타")
		)
		.from(member)
		.fetch();

	for (String s : result) {
		System.out.println("s = " + s);
	}
}
```

## 상수, 문자 더하기

상수가 필요하다면 `Expressions.constant(xxx)` 사용

```java
List<Tuple> result = queryFactory
			.select(member.username, Expressions.constant("A"))
			.from(member)
			.fetch();
```

위와 같이 최적화가 가능하면 SQL에 constant 값을 넘기지 않습니다. 상수를 더하는 것 처럼 최적화가 어려우면 SQL에 constant 값을 넘깁니다.

### 문자 더하기 concat

```java
List<String> result = queryFactory
			.select(member.username.concat("_").concat(member.age.stringValue()))
			.from(member)
			.where(member.username.eq("member1"))
			.fetch();
```

- 결과 : embmer1_10

`member.age.stringValue()` 부분이 중요한데, 문자가 아닌 다른 타입들은 `stringValue()`로 문자로 변환할 수 있습니다. 이 방법은 ENUM을 처리할 때도 자주 사용됩니다.

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/Ybt69