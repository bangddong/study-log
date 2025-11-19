---
emoji: "🚀"
title: "회원 도메인 개발"
date: 2025-03-18 13:55:00
update: 2025-03-18 13:55:00
tags:
  - Spring
  - JPA
series: "스프링 부트와 JPA 활용 1"
---

## MemberRepository

```java
@Repository
@RequiredArgsConstructor
public class MemberRepository {

	private final EntityManager em;

	public void save(Member member) {
		em.persist(member);
	}

	public Member findOne(Long id) {
		return em.find(Member.class, id);
	}

	public List<Member> findAll() {
		return em.createQuery("select m from Member m", Member.class)
				.getResultList();
	}

	public List<Member> findByName(String name) {
		return em.createQuery("select m from Member m where m.name = :name", Member.class)
				.setParameter("name", name)
				.getResultList();
	}

}
```

### **기술**

- @Repository: 스피링 빈으로 등록, JPA 예외를 스프링 기반 예외로 예외 변환
- @PersistenceContext: 엔티티 매니저(EntityManager) 주입
- @PersistenceUnit: 엔티티 매니저 팩토리(EntityManagerFactory) 주입

### **기능**

- save() : 엔티티 저장
- findOne() : ID에 맞는 엔티티 조회
- findAll(): 모든 엔티티 조회
- findByName: 이름에 맞는 엔티티 조회

## MemberService

```java
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class MemberService {

	private final MemberRepository memberRepository;

	/**
	 * 회원가입
	 */
	@Transactional
	public Long join(Member member) {
		validateDuplicateMember(member);
		memberRepository.save(member);
		return member.getId();
	}

	private void validateDuplicateMember(Member member) {
		List<Member> findMembers = memberRepository.findByName(member.getName());
		if (!findMembers.isEmpty()) {
			throw new IllegalStateException("이미 존재하는 회원입니다.");
		}
	}

	/**
	 * 전체 회원 조회
	 */
	public List<Member> findMembers() {
		return memberRepository.findAll();
	}

	/**
	 * 단일 회원 조회
	 */
	public Member findOne(Long memberId) {
		return memberRepository.findOne(memberId);
	}

}
```

### **기술**

- @Service
- @Transactional: 트랜잭션, 영속성 컨텍스트
    - readOnly=true: 데이터의 변경이 없는 읽기 전용 메서드에서 사용, 영속성 컨텍스트를 플러시 하지 않으므로 약간의 성능 향상
    - 데이터베이스 드라이버가 지원하면 DB에서 성능 향상
- @Autowired
    - 생성자 Injetion 많이 사용, 생성자가 하나면 생략 가능

### **기능**

- join()
- findMembers()
- findOne()

## MemberServiceTest

```java
@RunWith(SpringRunner.class)
@SpringBootTest
@Transactional
public class MemberServiceTest {

	@Autowired
	MemberService memberService;

	@Autowired
	MemberRepository memberRepository;

	@Test
	public void 회원가입() throws Exception {
	    // given
		Member member = new Member();
		member.setName("kim");

	    // when
		Long savedId = memberService.join(member);

		// then
		assertEquals(member, memberRepository.findOne(savedId));
	}

	@Test(expected = IllegalStateException.class)
	public void 중복_회원_예외() throws Exception {
		// given
		Member member1 = new Member();
		member1.setName("kim");

		Member member2 = new Member();
		member2.setName("kim");

		// when
		memberService.join(member1);
		memberService.join(member2);

		// then
		fail("예외가 발생해야 한다.");
	}

}
```

### **기술**

- @RunWith(SpringRunner.class): 스프링과 테스트 통합
- @SpringBootTest: 스프링 부트 띄우고 테스트(이게 없으면 @Autowired 다 실패)
- @Transactional: 반복 가능한 테스트 지원, 각각의 테스트를 실행할 때 마다 트랜잭션을 시작하고 **테스트가 끝나면 트랜잭션을 강제로 롤백** ( 이 어노테이션이 테스트 케이스에서 사용될 때만 롤백)

### **기능**

- 회원가입 테스트
- 중복 회원 예외처리 테스트

### 테스트 케이스를 위한 설정

테스트 케이스는 격리된 환경에서 실행하고, 끝나면 데이터를 초기화 하는 것이 좋습니다. 그런 면에서 메모리 DB를 사용하는 것이 가장 이상적입니다.

추가로 테스트 케이스를 위한 스프링 환경과, 일반적으로 애플리케이션을 실행하는 환경은 보통 다르므로 설정 파일을 다르게 사용하는 것이 좋습니다.

다음과 같이 간단하게 테스트용 설정 파일을 추가하면 격리된 환경에서 테스트를 실행할 수 있습니다.

**test/resources/application.yml**

```java
spring:
 #  datasource:
 #    url: jdbc:h2:mem:testdb
 #    username: sa
 #    password:
 #    driver-class-name: org.h2.Driver
 #  jpa:
 #    hibernate:
 #      ddl-auto: create
 #    properties:
 #      hibernate:
 #        show_sql: true
 #        format_sql: true
 #    open-in-view: false
 logging.level:
 org.hibernate.SQL: debug
 #  org.hibernate.type: trace

```

이제 테스트에서 스프링을 실행하면 위 파일을 읽고 없다면 기본 위치인 `src/resource/application.yml`을 읽습니다.

스프링 부트는 datasource 설정이 없으면, 기본적으로 메모리 DB를 사용하고, driver-class도 현재 등록된 라이브러리를 보고 찾아줍니다. 추가로 `ddl-auto`도 `create-drop`모드로 동작합니다. 따라서 데이터소스나, JPA 관련된 별도의 추가 설정을 하지 않아도 됩니다.

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/4Sbno