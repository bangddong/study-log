---
emoji: "🚀"
title: "트랜잭션 전파 - 기본"
date: 2025-08-25 00:00:00
update: 2025-08-25 00:00:00
tags:
  - Spring
  - Transaction
series: "Spring Transaction"
---

## 1. 커밋, 롤백

트랜잭션이 둘 이상 있을 때 어떻게 동작하는지 자세히 알아보고, 스프링이 제공하는 트랜잭션 전파(propagation)라는 개념도 알아보겠습니다.

트랜잭션 전파를 이해하는 과정을 통해서 스프링 트랜잭션의 동작 원리도 더 깊이있게 이해할 수 있습니다.

먼저 간단한 스프링 트랜잭션 코드를 통해 기본 원리를 학습하고, 이후에 실제 예제를 통해 어떻게 활용하는지 알아보겠습니다.

**BasicTxTest**

```java
package stduy.springtx.propagation;

import javax.sql.DataSource;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.interceptor.DefaultTransactionAttribute;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@SpringBootTest
public class BasicTxTest {
	
	@Autowired
	PlatformTransactionManager txManager;
	
	@TestConfiguration
	static class Config {
		@Bean
		public PlatformTransactionManager transactionManager(DataSource dataSource) {
			return new DataSourceTransactionManager(dataSource);
		}
	}
	
	@Test
	void commit() {
		log.info("트랜잭션 시작");
		TransactionStatus status = txManager.getTransaction(new DefaultTransactionAttribute());
		
		log.info("트랜잭션 커밋 시작");
		txManager.commit(status);
		log.info("트랜잭션 커밋 완료");
	}

	@Test
	void rollback() {
		log.info("트랜잭션 시작");
		TransactionStatus status = txManager.getTransaction(new DefaultTransactionAttribute());

		log.info("트랜잭션 롤백 시작");
		txManager.rollback(status);
		log.info("트랜잭션 롤백 완료");
	}
}
```

- `@TestConfiguration` : 해당 테스트에서 필요한 스프링 설정 추가
- `DataSoruceTransactionManager`를 스프링 빈으로 등록했으며 이후 트랜잭션 매니저인 `PlatformTransactionManager`를 주입 받으면 방금 등록한 `DataSourceTransactionManager`가 주입

**실행 전 트랜잭션 관련 로그 설정**

```java
// application.yml
logging:
  level:
    org:
      springframework:
        transaction:
          interceptor: TRACE
        jdbc:
          datasource:
            DataSourceTransactionManager: DEBUG
        orm:
          jpa:
            JpaTransactionManager: DEBUG
      hibernate:
        resource:
          transaction: DEBUG
        sql: DEBUG
```

**commit() - 실행 로그**

```java
트랜잭션 시작
Creating new transaction with name [null]
Acquired Connection
Switching JDBC Connection
트랜잭션 커밋 시작
Initiating transaction commit
Committing JDBC transaction on Connection
Releasing JDBC Connection
트랜잭션 커밋 완료
```

**rollback() - 실행 로그**

```java
트랜잭션 시작
Creating new transaction with name [null]
Acquired Connection
Switching JDBC Connection
트랜잭션 롤백 시작
Initiating transaction rollback
Rolling back JDBC transaction on Connection
Releasing JDBC Connection
트랜잭션 롤백 완료
```

## 2. 트랜잭션 두 번 사용

이번에는 트랜잭션이 각각 따로 사용되는 경우를 확인해보겠습니다.

아래 예제는 트랜잭션1이 완전히 끝난 후 트랜잭션2를 수행합니다.

**double_commit() - BasicTxTest**

```java
트랜잭션1 시작
Creating new transaction with name [null]
Acquired Connection [HikariProxyConnection@23436669 wrapping conn0
Switching JDBC Connection [HikariProxyConnection@23436669 wrapping conn0
트랜잭션1 커밋
Initiating transaction commit
Committing JDBC transaction on Connection [HikariProxyConnection@23436669 wrapping conn0
Releasing JDBC Connection [HikariProxyConnection@23436669 wrapping conn0
트랜잭션2 시작
Creating new transaction with name [null
Acquired Connection [HikariProxyConnection@1971275760 wrapping conn0
Switching JDBC Connection [HikariProxyConnection@1971275760 wrapping conn0
트랜잭션2 커밋
Initiating transaction commit
Committing JDBC transaction on Connection [HikariProxyConnection@1971275760 wrapping conn0
Releasing JDBC Connection [HikariProxyConnection@1971275760 wrapping conn0

```

**트랜잭션 1**

- `Acquired Connection [HikariProxyConnection@23436669 wrapping conn0`
    - 트랜잭션 1을 시작하고, 커넥션 풀에서 `conn0` 커넥션을 획득
- `Releasing JDBC Connection [HikariProxyConnection@23436669 wrapping conn0`
    - 트랜잭션 1을 커밋하고, 커넥션 풀에 `conn0` 커넥션을 반납

**트랜잭션 2**

- `Acquired Connection [HikariProxyConnection@1971275760 wrapping conn0`
    - 트랜잭션 2를 시작하고, 커넥션 풀에서 `conn0` 커넥션을 획득
- `Releasing JDBC Connection [HikariProxyConnection@1971275760 wrapping conn0`
    - 트랜잭션 2를 커밋하고, 커넥션 풀에 `conn0` 커넥션을 반납

로그를 보면 트랜잭션 1과 트랜잭션 2가 같은 `conn0` 커넥션을 사용중입니다. 이것은 중간에 커넥션 풀 때문에 그런 것입니다. 트랜잭션 1은 `conn0` 커넥션을 모두 사용하고 커넥션 풀에 반납까지 완료했고 이후 트랜잭션 2가 `conn0`를 커넥션 풀에서 획득한 것입니다. 따라서 둘은 완전히 다른 커넥션으로 인지하는게 맞습니다.

그렇다면 두 커넥션을 구분할 수 있는 방법은 없을까요?

히카리 커넥션 풀에서 커넥션을 획득하면 실제 커넥션을 그대로 반환하는 것이 아니라 내부 관리를 위해 히카리 프록시 커넥션이라는 객체를 생성해서 반환합니다. 물론 내부에는 실제 커넥션이 포함되어 있어 이 객체의 주소를 확인하면 커넥션 풀에서 획득한 커넥션을 구분할 수 있습니다.

- 트랜잭션 1: `Acquired Connection [HikariProxyConnection@23436669 wrapping conn0`
- 트랜잭션 2: `Acquired Connection [HikariProxyConnection@1971275760 wrapping conn0`

히카리 커넥션풀이 반환해주는 커넥션을 다루는 프록시 객체의 주소가 트랜잭션 1은 23436669, 트랜잭션 2는 1971275760으로 서로 다른 것을 확인할 수 있습니다.

결과적으로 `conn0`을 통해 커넥션이 재사용 된 것을 확인할 수 있고, 주소값을 통해 각각 커넥션 풀에서 커넥션을 조회한 것을 확인할 수 있습니다.

![image.png](images/img.png)

- 트랜잭션이 각각 수행되면서 사용되는 DB 커넥션도 각각 다름
- 이 경우 트랜잭션을 각자 관리하기 때문에 전체 트랜잭션을 묶을 수 없음. 예를 들어 트랜잭션 1이 커밋하고, 트랜잭션 2가 롤백하는 경우 트랜잭션 1에서 저장한 데이터는 커밋되고, 트랜잭션 2에서 저장한 데이터는 롤백

**double_commit_rollback()**

```java
@Test
void double_rollback() {
	log.info("트랜잭션1 시작");
	TransactionStatus tx1 = txManager.getTransaction(new DefaultTransactionAttribute());
	log.info("트랜잭션1 롤백");
	txManager.commit(tx1);

	log.info("트랜잭션2 시작");
	TransactionStatus tx2 = txManager.getTransaction(new DefaultTransactionAttribute());
	log.info("트랜잭션2 롤백");
	txManager.rollback(tx2);
}
```

- 예제에서는 트랜잭션 1은 커밋, 트랜잭션 2는 롤백
- 전체 트랜잭션을 묶지 않고 각각 관리했기 때문에, 트랜잭션 1에서 저장한 데이터는 커밋되고, 트랜잭션 2에서 저장한 데이터는 롤백

**실행 로그**

```java
트랜잭션1 시작
Creating new transaction with name [null]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT
Acquired Connection [HikariProxyConnection@416322179 wrapping conn0: url=jdbc:h2:mem:783dff80-d759-42c5-9872-f3937a733735 user=SA] for JDBC transaction
Switching JDBC Connection [HikariProxyConnection@416322179 wrapping conn0: url=jdbc:h2:mem:783dff80-d759-42c5-9872-f3937a733735 user=SA] to manual commit
트랜잭션1 커밋
Initiating transaction commit
Committing JDBC transaction on Connection [HikariProxyConnection@416322179 wrapping conn0: url=jdbc:h2:mem:783dff80-d759-42c5-9872-f3937a733735 user=SA]
Releasing JDBC Connection [HikariProxyConnection@416322179 wrapping conn0: url=jdbc:h2:mem:783dff80-d759-42c5-9872-f3937a733735 user=SA] after transaction
트랜잭션2 시작
Creating new transaction with name [null]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT
Acquired Connection [HikariProxyConnection@1637577782 wrapping conn0: url=jdbc:h2:mem:783dff80-d759-42c5-9872-f3937a733735 user=SA] for JDBC transaction
Switching JDBC Connection [HikariProxyConnection@1637577782 wrapping conn0: url=jdbc:h2:mem:783dff80-d759-42c5-9872-f3937a733735 user=SA] to manual commit
트랜잭션2 롤백
Initiating transaction rollback
Rolling back JDBC transaction on Connection [HikariProxyConnection@1637577782 wrapping conn0: url=jdbc:h2:mem:783dff80-d759-42c5-9872-f3937a733735 user=SA]
Releasing JDBC Connection [HikariProxyConnection@1637577782 wrapping conn0: url=jdbc:h2:mem:783dff80-d759-42c5-9872-f3937a733735 user=SA] after transaction
```

- 로그를 보면 트랜잭션 1은 커밋되었고, 트랜잭션 2는 롤백 되었음

![image.png](images/img_1.png)

## 3. 전파 기본

트랜잭션을 각각 사용하는 것이 아니라, 트랜잭션이 이미 진행중인데, 여기에 추가로 트랜잭션을 수행하면 어떻게 될까요?

기존 트랜잭션과 별도의 트랜잭션을 진행해야 하는지, 기존 트랜잭션을 그대로 이어 받아서 트랜잭션을 수행해야 하는지 결정해야 하는데 이런 경우 어떻게 동작할지 결정하는 것을 트랜잭션 전파(propagation)라 합니다.

참고로 스프링은 다양한 트랜잭션 전파 옵션을 제공하고 있습니다.

아래 예시는 `REQUIRED`를 기준으로 설명하며 옵션은 내용 마지막에 설명 예정입니다.

![image.png](images/img_2.png)

- 외부 트랜잭션이 수행중이고, 아직 끝나지 않았는데, 내부 트랜잭션이 수행
- 외부 트랜잭션이라고 이름 붙인 것은 둘 중 상대적으로 밖에 있기 때문에 외부 트랜잭션이라 호칭했으며 처음 시작된 트랜잭션으로 이해
- 내부 트랜잭션은 외부에 트랜잭션이 수행되고 있는 도중에 호출되기 때문에 마치 내부에 있는 것처럼 보여서 내부 트랜잭션이라 함

![image.png](images/img_3.png)

- 스프링에서 이 경우 외부 트랜잭션과 내부 트랜잭션을 묶어서 하나의 트랜잭션을 만들어줌.
- 내부 트랜잭션이 외부 트랜잭션에 참여하는 형태로 스프링 기본 동작이며 옵션을 통해 다른 동작 방식도 선택할 수 있음

### **물리 트랜잭션, 논리 트랜잭션**

![image.png](images/img_4.png)

- 스프링은 이해를 돕기 위해 논리 트랜잭션과 물리 트랜잭션이라는 개념을 나눔
- 논리 트랜잭션들은 하나의 물리 트랜잭션으로 묶임
- 물리 트랜잭션은 우리가 이해하는 실제 데이터베이스에 적용되는 트랜잭션을 뜻하며 실제 커넥션을 통해서 트랜잭션을 시작(`setAutocCommit(false))`하고, 실제 커넥션을 통해서 커밋, 롤백하는 단위
- 논리 트랜잭션은 트랜잭션 매니저를 통해 트랜잭션을 사용하는 단위
- 이러한 논리 트랜잭션 개념은 트랜잭션이 진행되는 중에 내부에 추가로 트랜잭션을 사용하는 경우에 나타남. 단순히 트랜잭션이 하나인 경우 둘을 구분하지 않음.
  (더 정확히는 `REQUIRED` 전파 옵션을 사용하는 경우에 나타남)

그럼 왜 이렇게 논리 트랜잭션과 물리 트랜잭션을 나누어 설명할까요?

트랜잭션이 사용중일 때 또 다른 트랜잭션이 내부에 사용되면 여러가지 복잡한 상황이 발생합니다. 이 때 논리 트랜잭션 개념을 도입하면 다음과 같은 단순한 원칙을 만들 수 있습니다.

**원칙**

- 모든 논리 트랜잭션이 커밋되어야 물리 트랜잭션이 커밋
- 하나의 논리 트랜잭션이라도 롤백되면 물리 트랜잭션은 롤백

풀어서 설명하자면 모든 트랜잭션 매니저를 커밋해야 물리 트랜잭션이 커밋되는 것이며 하나의 트랜잭션 매니저라도 롤백하면 물리 트랜잭션은 롤백됩니다.

![image.png](images/img_5.png)

- 모든 논리 트랜잭션이 커밋 되었으므로 물리 트랜잭션도 커밋

![image.png](images/img_6.png)

- 외부 논리 트랜잭션이 롤백 되었으므로 물리 트랜잭션은 롤백

![image.png](images/img_7.png)

- 내부 논리 트랜잭션이 롤백 되었으므로 물리 트랜잭션은 롤백

## 4. 전파 예제

예제 코드를 통해서 스프링 트랜잭션 전파를 살펴보겠습니다.

![image.png](images/img_8.png)

**inner_commit()**

```java
@Test
void inner_commit() {
	log.info("외부 트랜잭션 시작");
	TransactionStatus outer = txManager.getTransaction(new DefaultTransactionAttribute());
	log.info("outer.isNewTransaction()={}", outer.isNewTransaction());
	
	log.info("내부 트랜잭션 시작");
	TransactionStatus inner = txManager.getTransaction(new DefaultTransactionAttribute());
	log.info("outer.isNewTransaction()={}", inner.isNewTransaction());
	
	log.info("내부 트랜잭션 커밋");
	txManager.commit(inner);
	log.info("외부 트랜잭션 커밋");
	txManager.commit(outer);
}
```

- 외부 트랜잭션이 수행중인데, 내부 트랜잭션을 추가로 수행
- 외부 트랜잭션은 처음 수행된 트랜잭션으로 이 경우 신규 트랜잭션(`isNewTransaction=true`)이 됨
- 내부 트랜잭션을 시작하는 시점에는 이미 외부 트랜잭션이 진행중인 상태로 이 경우 내부 트랜잭션은 외부 트랜잭션에 참여
- 트랜잭션 참여
    - 내부 트랜잭션이 외부 트랜잭션에 참여한다는 뜻은 내부 트랜잭션이 외부 트랜잭션을 그대로 이어 받아서 따른다는 뜻
    - 다른 관점으로 보면 외부 트랜잭션의 범위가 내부 트랜잭션까지 넓어진다는 뜻
    - 외부에서 시작된 물리적인 트랜잭션의 범위가 내부 트랜잭션까지 넓어지나는 뜻
    - 정리하면 **외부 트랜잭션과 내부 트랜잭션이 하나의 물리 트랜잭션으로 묶이는 것**임
- 내부 트랜잭션은 이미 진행중인 외부 트랜잭션에 참여하며 이 경우 신규 트랜잭션이 아님
  (`isNewTransaction=false`)
- 예제에서는 둘 다 커밋 성공

이 예제에서는 외부 트랜잭션과 내부 트랜잭션이 하나의 물리 트랜잭션으로 묶인다고 설명했습니다.

그런데 코드를 잘 보면 커밋을 두 번 호출하고 있는데 트랜잭션을 생각해보면 하나의 커넥션에 커밋은 한 번만 호출할 수 있습니다.

커밋이나 롤백을 하면 해당 트랜잭션은 끝나버립니다.

스프링은 어떻게 외부 트랜잭션과 내부 트랜잭션을 묶어서 하나의 물리 트랜잭션으로 묶어서 동작하게 되는지 알아보겠습니다.

실행 결과

```java
외부 트랜잭션 시작
Creating new transaction with name [null]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT
Acquired Connection [HikariProxyConnection@1284775193 wrapping conn0: url=jdbc:h2:mem:ef8d598e-fe02-448c-8306-5370d1200375 user=SA] for JDBC transaction
Switching JDBC Connection [HikariProxyConnection@1284775193 wrapping conn0: url=jdbc:h2:mem:ef8d598e-fe02-448c-8306-5370d1200375 user=SA] to manual commit
outer.isNewTransaction()=true

내부 트랜잭션 시작
Participating in existing transaction
outer.isNewTransaction()=false
내부 트랜잭션 커밋

외부 트랜잭션 커밋
Initiating transaction commit
Committing JDBC transaction on Connection [HikariProxyConnection@1284775193 wrapping conn0: url=jdbc:h2:mem:ef8d598e-fe02-448c-8306-5370d1200375 user=SA]
Releasing JDBC Connection [HikariProxyConnection@1284775193 wrapping conn0: url=jdbc:h2:mem:ef8d598e-fe02-448c-8306-5370d1200375 user=SA] after transaction
```

- 내부 트랜잭션을 시작할 때 `Participating in existing transaction` 이라는 메시지를 확인할 수 있음. 이 메시지는 내부 트랜잭션이 기존에 존재하는 외부 트랜잭션에 참여한다는 뜻
- 실행 결과를 보면 외부 트랜잭션을 시작하거나 커밋할 때는 DB 커넥션을 통한 물리 트랜잭션을 시작(`manual commit`)하고, DB 커넥션을 통해 커밋 하는 것을 확인할 수 있음. 그런데 내부 트랜잭션을 시작하거나 커밋할 때는 DB 커넥션을 통해 커밋하는 로그를 전혀 확인할 수 없음
- 정리하면 외부 트랜잭셔만 물리 트랜잭션을 시작하고, 커밋함
- 만약 내부 트랜잭션이 실제 물리 트랜잭션을 커밋하면 트랜잭션이 끝나버리기 때문에, 트랜잭션을 처음 시작한 외부 트랜잭션까지 이어갈 수 없음. 따라서 내부 트랜잭션은 DB 커넥션을 통한 물리 트랜잭션을 커밋하면 안됨
- 스프링은 이렇게 여러 트랜잭션이 함께 사용되는 경우, **처음 트랜잭션을 시작한 외부 트랜잭션이 실제 물리 트랜잭션을 관리**하도록 하며 이를 통해 트랜잭션 중복 커밋 문제를 해결

![image.png](images/img_9.png)

트랜잭션 전파가 실제 어떻게 동작하는지 그림으로 알아보겠습니다.

![image.png](images/img_10.png)

**요청 흐름 - 외부 트랜잭션**

1. `txManager.getTransaction()`을 호출해서 외부 트랜잭션을 시작
2. 트랜잭션 매니저는 데이터소스를 통해 커넥션 생성
3. 생성한 커넥션을 수동 커밋 모드(`setAutoComit(false))`로 설정 (**물리 트랜잭션 시작**)
4. 트랜잭션 매니저는 트랜잭션 동기화 매니저에 커넥션을 보관
5. 트랜잭션 매니저는 트랜잭션을 생성한 결과를 `TransactionStatus`에 담아서 반환하는데, 여기에 신규 트랜잭션의 여부가 담겨 있다. `isNewTransaction`를 통해 신규 트랜잭션 여부를 확인할 수 있는데 트랜잭션을 처음 시작했으니 신규 트랜잭션임
6. 로직1이 사용되고, 커넥션이 필요한 경우 트랜잭션 동기화 매니저를 통해 트랜잭션이 적용된 커넥션을 획득 후 사용

**요청 흐름 - 내부 트랜잭션**

1. `txManager.getTransaction()`를 호출해서 내부 트랜잭션 시작
2. 트랜잭션 매니저는 트랜잭션 동기화 매니저를 통해서 기존 트랜잭션이 존재하는지 확인
3. 기존 트랜잭션이 존재하므로 기존 트랜잭션에 참여. 기존 트랜잭션에 참여한단느 뜻은 사실 아무것도 하지 않는다는 뜻
    - 이미 기존 트랜잭션인 외부 트랜잭션에서 물리 트랜잭션을 시작했다. 그리고 물리 트랜잭션이 시작된 커넥션을 트랜잭션 동기화 매니저에 담아두었음.
    - 따라서 이미 물리 트랜잭션이 진행중이므로 그냥 두면 이후 로직이 기존에 시작된 트랜잭션을 자연스럽게 사용하게 되는 것
    - 이후 로직은 자연스럽게 트랜잭션 동기화 매니저에 보관된 기존 커넥션을 사용
4. 트랜잭션 매니저는 트랜잭션을 생성한 결과를 `TransactionStatus`에 담아 반환하는데, 여기에서 `isNewTransaction`을 통해 신규 트랜잭션 여부를 확인할 수 있다. 기존 트랜잭션에 참여했기 때문에 신규 트랜잭션이 아님. (`false`)
5. 로직 2가 사용되고, 커넥션이 필요한 경우 트랜잭션 동기화 매니저를 통해 외부 트랜잭션이 보관한 커넥션을 획득해서 사용

![image.png](images/img_11.png)

**응답 흐름 - 내부 트랜잭션**

1. 로직2가 끝나고 트랜잭션 매니저를 통해 내부 트랜잭션을 커밋
2. 트랜잭션 매니저는 커밋 시점에 신규 트랜잭션 여부에 따라 다르게 동작함. 이 경우 신규 트랜잭션이 아니기 때문에 실제 커밋을 호출하지 않음. 이 부분이 중요한데, 실제 커넥션에 커밋이나 롤백을 호출하면 물리 트랜잭션이 끝나버린다. 하지만 아직 트랜잭션이 끝난 것이 아니기 때문에 실제 커밋을 호출하면 안되고 물리 트랜잭션은 외부 트랜잭션을 종료할 때 까지 이어져야 함.

**응답 흐름 - 외부 트랜잭션**

1. 로직1이 끝나고 트랜잭션 매니저를 통해 외부 트랜잭션을 커밋
2. 트랜잭션 매니저는 커밋 시점에 신규 트랜잭션 여부에 따라 다르게 동작. 외부 트랜잭션은 신규 트랜잭션으로 DB 커넥션에 실제 커밋을 호출
3. 트랜잭션 매니저에 커밋하는 것이 논리적인 커밋이라면, 실제 커넥션에 커밋하는 것을 물리 커밋이라 할 수 있음. 실제 데이터베이스에 커밋이 반영되고, 물리 트랜잭션도 끝남

**핵심 정리**

여기서 핵심은 트랜잭션 매니저에 커밋을 호출한다고해서 항상 실제 커넥션에 물리 커밋이 발생하지 않는다는 점입니다. 신규 트랜잭션인 경우에만 실제 커넥션을 사용해서 물리 커밋과 롤백을 수행합니다. 신규 트랜잭션이 아니면 실제로는 물리 커넥션을 사용하지 않습니다.

이렇게 트랜잭션이 내부에서 추가로 사용되면 트랜잭션 매니저에 커밋하는 것이 항상 물리 커밋으로 이어지지는 않습니다. 그래서 이 경우 논리 트랜잭션과 물리 트랜잭션을 나누게 됩니다. 또는 외부 트랜잭션과 내부 트랜잭션으로 나누어 설명하기도 합니다. 트랜잭션이 내부에서 추가로 사용되면, 트랜잭션 매니저를 통해 논리 트랜잭션을 관리하고, 모든 논리 트랜잭션이 커밋되면 물리 트랜잭션이 커밋된다고 이해하면 됩니다.

## 5. 외부 롤백

이번에는 내부 트랜잭션은 커밋되는데, 외부 트랜잭션이 롤백되는 상황을 살펴보겠습니다.

![image.png](images/img_12.png)

논리 트랜잭션이 하나라도 롤백되면 전체 물리 트랜잭션은 롤백됩니다. 따라서 이 경우 내부 트랜잭션을 커밋했어도, 내부 트랜잭션 안에서 저장한 데이터도 모두 함께 롤백됩니다.

**outer_rollback() - BasicTxTest 추가**

```java
@Test
void outer_rollback() {
	log.info("외부 트랜잭션 시작");
	TransactionStatus outer = txManager.getTransaction(new DefaultTransactionAttribute());

	log.info("내부 트랜잭션 시작");
	TransactionStatus inner = txManager.getTransaction(new DefaultTransactionAttribute());
	log.info("내부 트랜잭션 커밋");
	txManager.commit(inner);

	log.info("외부 트랜잭션 롤백");
	txManager.rollback(outer);
}
```

**실행 결과**

```java
외부 트랜잭션 시작
Creating new transaction with name [null]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT
Acquired Connection [HikariProxyConnection@210688344 wrapping conn0: url=jdbc:h2:mem:b3ce2f97-9b9f-4368-b615-3b00a6f984e6 user=SA] for JDBC transaction
Switching JDBC Connection [HikariProxyConnection@210688344 wrapping conn0: url=jdbc:h2:mem:b3ce2f97-9b9f-4368-b615-3b00a6f984e6 user=SA] to manual commit
내부 트랜잭션 시작
Participating in existing transaction
내부 트랜잭션 커밋
외부 트랜잭션 롤백
Initiating transaction rollback
Rolling back JDBC transaction on Connection [HikariProxyConnection@210688344 wrapping conn0: url=jdbc:h2:mem:b3ce2f97-9b9f-4368-b615-3b00a6f984e6 user=SA]
Releasing JDBC Connection [HikariProxyConnection@210688344 wrapping conn0: url=jdbc:h2:mem:b3ce2f97-9b9f-4368-b615-3b00a6f984e6 user=SA] after transaction
```

- 외부 트랜잭션이 물리 트랜잭션을 시작하고 롤백하는 것을 확인할 수 있음
- 내부 트랜잭션은 앞서 배운대로 직접 물리 트랜잭션에 관여하지 않음
- 결과적으로 외부 트랜잭션에서 시작한 물리 트랜잭션의 범위가 내부 트랜잭션까지 사용됨. 이후 외부 트랜잭션이 롤백되면서 전체 내용은 모두 롤백

**응답 흐름**

![image.png](images/img_13.png)

요청 흐름은 앞의 내용과 동일하여 생략했으며 응답 흐름에 집중해서 살펴보겠습니다.

**응답 흐름 - 내부 트랜잭션**

1. 로직 2가 끝나고 트랜잭션 매니저를 통해 내부 트랜잭션을 커밋
2. 트랜잭션 매니저는 커밋 시점에 신규 트랜잭션 여부에 따라 다르게 동작. 이 경우 신규 트랜잭션이 아니기 때문에 실제 커밋을 호출하지는 않음. 실제 커넥션에 커밋이나 롤백을 호출하면 물리 트랜잭션이 끝나버리는데 아직 트랜잭션이 끝난 것이 아니기 때문에 실제 커밋을 호출하면 안되며 물리 트랜잭션은 외부 트랜잭션을 종료할 때 까지 이어져야 함.

**응답 흐름 - 외부 트랜잭션**

1. 로직 1이 끝나고 트랜잭션 매니저를 통해 외부 트랜잭션을 롤백
2. 트랜잭션 매니저는 롤백 시점에 신규 트랜잭션 여부에 따라 다르게 동작. 외부 트랜잭션은 신규 트랜잭션이기 때문에 실제 DB 커넥션에 실제 롤백을 호출
3. 트랜잭션 매니저에 롤백하는 것이 논리적인 롤백이라면, 실제 커넥션에 롤백하는 것을 물리 롤백이라 할 수 있음. 실제 데이터베이스에 롤백이 반영되고, 물리 트랜잭션도 끝남

앞의 내용에서 커밋을 롤백으로 바꾸었을 뿐 같은 내용이기 때문에 크게 어렵지는 않습니다.

## 6. 내부 롤백

이번에는 내부 트랜잭션은 롤백되는데, 외부 트랜잭션이 커밋되는 상황을 살펴보겠습니다.

![image.png](images/img_14.png)

이 상황은 겉으로 보기에는 단순하지만, 실제로는 단순하지 않습니다. 내부 트랜잭션이 롤백을 했지만, 내부 트랜잭션은 물리 트랜잭션에 영향을 주지 않습니다. 그런데 외부 트랜잭션은 커밋을 해버립니다. 지금까지 학습한 내용을 돌아보면 외부 트랜잭션만 물리 트랜잭션에 영향을 주기 때문에 물리 트랜잭션이 커밋이 될 것 같습니다. 전체를 로백해야 하는데 스프링은 이 문제를 어떻게 해결할까요?

**inner_rollback()**

```java
@Test
void inner_rollback() {
	log.info("외부 트랜잭션 시작");
	TransactionStatus outer = txManager.getTransaction(new DefaultTransactionAttribute());

	log.info("내부 트랜잭션 시작");
	TransactionStatus inner = txManager.getTransaction(new DefaultTransactionAttribute());
	log.info("내부 트랜잭션 롤백");
	txManager.rollback(inner);

	log.info("외부 트랜잭션 커밋");
	assertThatThrownBy(() -> txManager.commit(outer))
		.isInstanceOf(UnexpectedRollbackException.class);
}
```

- 실행 결과를 보면 마지막에 외부 트랜잭션을 커밋할 때 `UnexceptedRollbackExcetpion.class`이 발생하는 것을 확인할 수 있음.

**실행 결과**

```java
외부 트랜잭션 시작
Creating new transaction with name [null]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT
Acquired Connection [HikariProxyConnection@506972944 wrapping conn0: url=jdbc:h2:mem:4f521958-dd63-4b41-9d78-5ad065752570 user=SA] for JDBC transaction
Switching JDBC Connection [HikariProxyConnection@506972944 wrapping conn0: url=jdbc:h2:mem:4f521958-dd63-4b41-9d78-5ad065752570 user=SA] to manual commit
내부 트랜잭션 시작
Participating in existing transaction
내부 트랜잭션 커밋
Participating transaction failed - marking existing transaction as rollback-only
Setting JDBC transaction [HikariProxyConnection@506972944 wrapping conn0: url=jdbc:h2:mem:4f521958-dd63-4b41-9d78-5ad065752570 user=SA] rollback-only
외부 트랜잭션 커밋
Global transaction is marked as rollback-only but transactional code requested commit
Initiating transaction rollback
Rolling back JDBC transaction on Connection [HikariProxyConnection@506972944 wrapping conn0: url=jdbc:h2:mem:4f521958-dd63-4b41-9d78-5ad065752570 user=SA]
Releasing JDBC Connection [HikariProxyConnection@506972944 wrapping conn0: url=jdbc:h2:mem:4f521958-dd63-4b41-9d78-5ad065752570 user=SA] after transaction
```

- 외부 트랜잭션 시작
    - 물리 트랜잭션도 시작
- 내부 트랜잭션 시작
    - `Participating in existing transaction`
    - 기존 트랜잭션에 참여
- 내부 트랜잭션 롤백
    - `Participating transaction failed - markin existing transaction as rollback-only`
    - 내부 트랜잭션을 롤백하면 실제 물리 트랜잭션은 롤백하지 않음. 대신 기존 트랜잭션을 롤백 전용으로 표시
- 외부 트랜잭션 커밋
    - 외부 트랜잭션 커밋
    - `Global transaction is marked as rollback-only`
    - 커밋을 호출했지만, 전체 트랜잭션이 롤백 전용으로 표시되어 있어 물리 트랜잭션을 롤백

![image.png](images/img_15.png)

**응답 흐름 - 내부 트랜잭션**

1. 로직 2가 끝나고 트랜잭션 매니저를 통해 내부 트랜잭션 롤백 (로직 2에 문제가 있어 롤백한다고 가정)
2. 트랜잭션 매니저는 롤백 시점에 신규 트랜잭션 여부에 따라 다르게 동작. 이 경우 신규 트랜잭션이 아니기 때문에 실제 롤백을 호출하지 않음. 이 경우도 트랜잭션이 아직 끝난게 아니기 때문에 실제 롤백을 호출하면 안됨
3. 내부 트랜잭션은 물리 트랜잭션을 롤백하지 않는 대신 트랜잭션 동기화 매니저에 `rollbackOnly=true`표시

**응답 흐름 - 외부 트랜잭션**

1. 로직 1이 끝나고 트랜잭션 매니저를 통해 외부 트랜잭션 커밋
2. 트랜잭션 매니저는 커밋 시점에 신규 트랜잭션 여부에 따라 다르게 동작. 외부 트랜잭션은 신규 트랜잭션으로 DB 커넥션에 실제 커밋을 호출해야 함. 이 때 먼저 트랜잭션 동기화 매니저에 롤백 전용(`rollbackOnly=true`) 표시가 있는지 확인. 해당 표시가 있으면 커밋이 아닌 로백을 진행
3. 실제 데이터베이스에 롤백이 반영되고, 물리 트랜잭션 종료
4. 트랜잭션 매니저에 커밋을 호출한 개발자 입장에서는 커밋을 기대했으나 롤백 전용으로 인해 롤백 발생
    - 시스템 입장에서는 커밋을 호출했지만 롤백이 되었기 때문에 이는 분명하게 기록을 해야함
    - 예를 들어 고객은 주문이 성공했다고 생각했으나, 실제로는 롤백이 발생되어 주문이 생성되지 않음
    - 스프링은 이 경우 `UnexpectedRollbackException` 런타임 예외를 발생시켜 커밋을 시도했으나 기대하지 않은 롤백이 발생했다는 것을 명확하게 알려줌

**정리**

- 논리 트랜잭션이 하나라도 롤백되면 물리 트랜잭션은 롤백
- 내부 논리 트랜잭션이 롤백되면 롤백 전용 마크를 표시
- 외부 트랜잭션을 커밋할 때 롤백 전용 마크를 확인. 롤백 전용 마크가 표시되어 있으면 물리 트랜잭션을 롤백하고, `UnexpectedRollbackException` 예외를 발생

**참고**

애플리케이션 개발에서 중요한 기본 원칙은 모호함을 제거하는 것입니다. 개발은 명확해야 합니다. 이렇게 커밋을 호출했는데, 내부에서 롤백이 발생한 경우 모호하게 두면 아주 심각한 문제가 발생할 수 있습니다. 이렇게 기대한 결과가 다른 경우 예외를 발생시켜 명확하게 문제를 알려주는 것이 좋은 설계라고 할 수 있습니다.

## 7. REQUIRES_NEW

이번에는 외부 트랜잭션과 내부 트랜잭션을 완전히 분리해서 사용하는 방법에 대해서 알아보겠습니다. 외부 트랜잭션과 내부 트랜잭션을 완전히 분리해서 각각 별도의 물리 트랜잭션을 사용하는 방법입니다. 그래서 커밋과 롤백도 각각 별도로 이루어지게 됩니다.

이 방법은 내부 트랜잭션에 문제가 발생해서 롤백해도, 외부 트랜잭션에는 영향을 주지 않습니다. 반대로 외부 트랜잭션에 문제가 발생해도 내부 트랜잭션에 영향을 주지 않습니다. 이 방법을 사용하는 구체적인 예는 이후에 알아보고 지금은 작동 원리를 이해해보겠습니다.

![image.png](images/img_16.png)

- 이렇게 물리 트랜잭션 자체를 분리하려면 시작시 `REQUIRES_NEW` 옵션을 사용하면 됨
- 외부 트랜잭션과 내부 트랜잭션이 각각 별도의 물리 트랜잭션을 가짐
- 별도의 물리 트랜잭션을 가진다는 뜻은 DB 커넥션을 따로 사용한다는 뜻
- 이 경우 내부 트랜잭션이 롤백되면서 로직 2가 롤백되어도 로직 1에서 저장한 데이터에는 영향을 주지 않음.
- 최종적으로는 로직 2는 롤백되고, 로직 1은 커밋

**inner_rollback_requires_new()**

```java
@Test
public void inner_rollback_requires_new() throws Exception {
	log.info("외부 트랜잭션 시작");
	TransactionStatus outer = txManager.getTransaction(new DefaultTransactionAttribute());
	log.info("outer.isNewTransaction()={}", outer.isNewTransaction());

	log.info("내부 트랜잭션 시작");
	DefaultTransactionAttribute definition = new DefaultTransactionAttribute();
	definition.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
	TransactionStatus inner = txManager.getTransaction(definition);
	log.info("inner.isNewTransaction()={}", outer.isNewTransaction());

	log.info("내부 트랜잭션 롤백");
	txManager.rollback(inner);

	log.info("외부 트랜잭션 커밋");
	txManager.commit(outer);
}
```

- 내부 트랜잭션을 시작할 때 전파 옵션인 REQUIRES_NEW 지정
- 이 전파 옵션을 사용하면 내부 트랜잭션을 시작할 때 기존 트랜잭션에 참여가 아닌 새로운 물리 트랜잭션을 만들어 시작

**실행결과**

```java
외부 트랜잭션 시작
Creating new transaction with name [null]: PROPAGATION_REQUIRED,ISOLATION_DEFAULT
Acquired Connection [HikariProxyConnection@1380499546 wrapping conn0: url=jdbc:h2:mem:e5aac86d-ecc4-4a13-b54b-c917bd15cf92 user=SA] for JDBC transaction
Switching JDBC Connection [HikariProxyConnection@1380499546 wrapping conn0: url=jdbc:h2:mem:e5aac86d-ecc4-4a13-b54b-c917bd15cf92 user=SA] to manual commit
outer.isNewTransaction()=true
내부 트랜잭션 시작
Suspending current transaction, creating new transaction with name [null]
Acquired Connection [HikariProxyConnection@1885867912 wrapping conn1: url=jdbc:h2:mem:e5aac86d-ecc4-4a13-b54b-c917bd15cf92 user=SA] for JDBC transaction
Switching JDBC Connection [HikariProxyConnection@1885867912 wrapping conn1: url=jdbc:h2:mem:e5aac86d-ecc4-4a13-b54b-c917bd15cf92 user=SA] to manual commit
inner.isNewTransaction()=true
내부 트랜잭션 롤백
Initiating transaction rollback
Rolling back JDBC transaction on Connection [HikariProxyConnection@1885867912 wrapping conn1: url=jdbc:h2:mem:e5aac86d-ecc4-4a13-b54b-c917bd15cf92 user=SA]
Releasing JDBC Connection [HikariProxyConnection@1885867912 wrapping conn1: url=jdbc:h2:mem:e5aac86d-ecc4-4a13-b54b-c917bd15cf92 user=SA] after transaction
Resuming suspended transaction after completion of inner transaction
외부 트랜잭션 커밋
Initiating transaction commit
Committing JDBC transaction on Connection [HikariProxyConnection@1380499546 wrapping conn0: url=jdbc:h2:mem:e5aac86d-ecc4-4a13-b54b-c917bd15cf92 user=SA]
Releasing JDBC Connection [HikariProxyConnection@1380499546 wrapping conn0: url=jdbc:h2:mem:e5aac86d-ecc4-4a13-b54b-c917bd15cf92 user=SA] after transaction
```

**외부 트랜잭션 시작**

- 외부 트랜잭션을 시작하면서 커넥션(`conn0`)을 획득하고 `manual commit`으로 변경해서 물리 트랜잭션 시작
- 외부 트랜잭션은 신규 트랜잭션임 (`true`)

**내부 트랜잭션 시작**

- 내부 트랜잭션을 시작하면서 커넥션을(`conn1`) 획득하고 `manual commit`으로 변경해서 물리 트랜잭션 시작
- 내부 트랜잭션은 외부 트랜잭션에 참여하는 것이 아니라, `REQURIES_NEW` 옵션을 사용했기 때문에 완전히 새로운 신규 트랜잭션으로 생성 (`true`)

**내부 트랜잭션 롤백**

- 내부 트랜잭션 롤백
- 내부 트랜잭션은 신규 트랜잭션이기 때문에 실제 물리 트랜잭션 롤백
- 내부 트랜잭션은 `conn1`을 사용중이기 때문에 해당 커넥션 롤백수행

**외부 트랜잭션 커밋**

- 외부 트랜잭션 커밋
- 외부 트랜잭션은 신규 트랜잭션이기 때문에 실제 물리 트랜잭션 커밋
- 외부 트랜잭션은 `conn0`을 사용중이기 때문에 해당 커넥션 커밋 수행

![image.png](images/img_17.png)

![image.png](images/img_18.png)

**요청 흐름 - 외부 트랜잭션**

1. `txManager.getTransaction()`을 호출해서 외부 트랜잭션 시작
2. 트랜잭션 매니저는 데이터소스를 통해 커넥션 생성
3. 생성한 커넥션을 수동 커밋 모드(`setAutoCommit(false))`로 설정 - **물리 트랜잭션 시작**
4. 트랜잭션 매니저는 트랜잭션 동기화 매니저에 커넥션을 보관
5. 트랜잭션 매니저는 트랜잭션을 생성한 결과를 `TransactionStatus`에 담아서 반환하는데, 여기에 신규 트랜잭션 여부가 담겨 있음. `isNewTransaction`을 통해 신규 트랜잭션 여부를 확인할 수 있는데 트랜잭션을 처음 시작했으니 신규 트랜잭션임
6. 로직 1이 사용되고, 커넥션이 필요한 경우 트랜잭션 동기화 매니저를 통해 트랜잭션이 적용된 커넥션을 획득해서 사용

**요청 흐름 - 내부 트랜잭션**

1. `REQUIRES_NEW` 옵션과 함께 `txManager.getTransaction()`을 호출해서 내부 트랜잭션을 시작
    - 트랜잭션 매니저는 `REQUIRES_NEW` 옵션을 확인하고, 기존 트랜잭션에 참여하는 것이 아니라 새로운 트랜잭션을 시작
2. 트랜잭션 매니저는 데이터소스를 통해 커넥션을 생성
3. 생성한 커넥션을 수동 커밋 모드(`setAUtoCommit(false))`로 설정 - 물리 트랜잭션 시작
4. 트랜잭션 매니저는 트랜잭션 동기화 매니저에 커넥션을 보관
    - 이 때 `conn1`은 잠시 보류되고, 지금부터는 `conn2`가 사용됨 ( 내부 트랜잭션 완료시까지 `conn2`가 사용)
5. 트랜잭션 매니저는 신규 트랜잭션의 생성한 결과 반환 (`isNewTransaction == true`)
6. 로직 2가 사용되고, 커넥션이 필요한 경우 트랜잭션 동기화 매니저가 있는 `conn2` 커넥션을 획득해서 사용

![image.png](images/img_19.png)

응답 흐름 - 내부 트랜잭션

1. 로직 2가 끝나고 트랜잭션 매니저를 통해 내부 트랜잭션을 롤백 (로직 2에 문제가 있어 롤백한다고 가정)
2. 트랜잭션 매니저는 롤백 시점에 신규 트랜잭션 여부에 따라 다르게 동작. 현재 내부 트랜잭션은 신규 트랜잭션으로 실제 롤백을 호출
3. 내부 트랜잭션이 `conn2` 물리 트랜잭션 롤백
    - 트랜잭션이 종료되고, `conn2`는 종료되거나, 커넥션 풀에 반납
    - 이후에 `conn1`의 보류가 끝나고, 다시 `conn1`을 사용

**응답 흐름 - 외부 트랜잭션**

1. 외부 트랜잭션에 커밋을 요청
2. 외부 트랜잭션은 신규 트랜잭션이기 때문에 물리 트랜잭션을 커밋
3. 이 때 `rollbackOnly` 설정을 체크. `rollbackOnly` 설정이 없으므로 커밋
4. 본인이 만든 `conn1` 커넥션을 통해 물리 트랜잭션을 커밋
    - 트랜잭션이 종료되고, `conn1`은 종료되거나, 커넥션 풀에 반납됨

**정리**

- `REQUIRES_NEW` 옵션을 사용하면 물리 트랜잭션이 명확하게 분리
- `REQUIRES_NEW`를 사용하면 DB 커넥션이 동시에 2개 사용되다는 점을 주의

## 8. 다양한 전파 옵션

스프링은 다양한 트랜잭션 전파 옵션을 제공합니다. 전파 옵션에 별도의 설정을 하지 않으면 `REQUIRED`가 기본으로 사용됩니다. 실무에서도 대부분 `REQUIRED` 옵션을 사용합니다. 그리고 아주 가끔 `REQUIRES_NEW`를 사용하고, 나머지는 거의 사용하지 않습니다. 그래서 나머지 옵션은 이런 것이 있다는 정도로만 알아두고 넘어가겠습니다.

**REQUIRED**

가장 많으 사용하는 기본 설정으로 기존 트랜잭션이 없으면 생성하고, 있으면 참여합니다. 트랜잭션이 필수라는 의미로 이해하면 쉽습니다.

**REQUIRES_NEW**

항상 새로운 트랜잭션을 생성합니다.

**SUPPORT**

트랜잭션을 지원한다는 뜻입니다. 기존 트랜잭션이 없으면, 없는대로 진행하고, 있으면 참여합니다.

**NOT_SUPPORT**
트랜잭션을 지원하지 않는다는 의미입니다. 기존 트랜잭션이 있어도 잠시 보류시키고 트랜잭션 없이 진행합니다.

**MANDATORY**

의무사항입니다. 트랜잭션이 반드시 있어야하며 없으면 예외가 발생합니다.

**NEVER**

트랜잭션을 사용하지 않는다는 의미입니다. 기존 트랜잭션이 있으면 예외가 발생하는데 기존 트랜잭션도 허용하지 않는 강한 부정의 의미로 이해하면 됩니다.

**NESTED**

기존 트랜잭션이 없으면 새로운 트랜잭션을 생성하고, 있으면 중첩 트랜잭션을 만듭니다. 중첩 트랜잭션은 외부 트랜잭션의 영향을 받지만, 외부 트랜잭션에 영향을 주지는 않습니다. 따라서 롤백 되어도 외부 트랜잭션은 커밋할 수 있지만 외부 트랜잭션이 롤백되면 내부 트랜잭션도 롤백됩니다.

※JDBC savepoint를 활용한 기능으로 DB 드라이버에서 해당 기능을 지원하는지 확인이 필요하며 JPA에서는 지원하지 않습니다.

**트랜잭션 전파와 옵션**

`isolation`, `timeout`, `readOnly`는 트랜잭션이 처음 시작될 때만 적용되며 트랜잭션에 참여하는 경우에는 적용되지 않습니다. 예를 들어 `REQUIRED`를 통한 트랜잭션 시작, `REQUIRES_NEW`를 통한 트랜잭션 시작 시점에만 적용됩니다.

**이 링크를 통해 구매하시면 제가 수익을 받을 수 있어요. 🤗**

https://inf.run/G1rX9