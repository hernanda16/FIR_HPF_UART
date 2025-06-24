library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity FRAMING is
    port (
        CLOCK     : in  std_logic;
        RESET     : in  std_logic;
        DATA0     : in  std_logic_vector(11 downto 0);
        DATA1     : in  std_logic_vector(11 downto 0);
        TX_DV     : out std_logic;
        TX_BYTE   : out std_logic_vector(7 downto 0);
        TX_DONE   : in  std_logic;
        TX_ACTIVE : in  std_logic
    );
end entity FRAMING;

architecture RTL of FRAMING is
    type state_type is (IDLE, SEND_HEADER, SEND_D0_HIGH, SEND_D0_LOW, 
                       SEND_D1_HIGH, SEND_D1_LOW, SEND_EOL, WAIT_TX_COMPLETE, WAIT_DELAY);
    signal state : state_type := IDLE;

    signal tx_dv_reg        : std_logic := '0';
    signal byte_to_send     : std_logic_vector(7 downto 0);
    signal delay_counter    : integer := 0;
    constant interframe_delay : integer := 0; -- 1ms @ 50MHz
    signal adc_data0_reg    : std_logic_vector(11 downto 0);
    signal adc_data1_reg    : std_logic_vector(11 downto 0);
    signal tx_done_prev     : std_logic := '0';

begin

    TX_DV   <= tx_dv_reg;
    TX_BYTE <= byte_to_send;

    process(CLOCK)
    begin
        if rising_edge(CLOCK) then
            if RESET = '0' then
                state           <= IDLE;
                tx_dv_reg       <= '0';
                delay_counter   <= 0;
                byte_to_send    <= x"00";
                adc_data0_reg   <= (others => '0');
                adc_data1_reg   <= (others => '0');
                tx_done_prev    <= '0';
            else
                tx_done_prev <= TX_DONE;
                
                case state is
                    when IDLE =>
                        if TX_ACTIVE = '0' then
                            adc_data0_reg <= DATA0;
                            adc_data1_reg <= DATA1;
                            byte_to_send  <= x"53"; -- 'S' start frame
                            tx_dv_reg     <= '1';
                            state         <= SEND_HEADER;
                        end if;

                    when SEND_HEADER =>
                        if TX_ACTIVE = '1' then
                            tx_dv_reg <= '0';
                        end if;
                        if TX_DONE = '1' and tx_done_prev = '0' then
                            byte_to_send <= adc_data0_reg(11 downto 4);
                            tx_dv_reg    <= '1';
                            state        <= SEND_D0_HIGH;
                        end if;

                    when SEND_D0_HIGH =>
                        if TX_ACTIVE = '1' then
                            tx_dv_reg <= '0';
                        end if;
                        if TX_DONE = '1' and tx_done_prev = '0' then
                            byte_to_send <= adc_data0_reg(3 downto 0) & "0000";
                            tx_dv_reg    <= '1';
                            state        <= SEND_D0_LOW;
                        end if;

                    when SEND_D0_LOW =>
                        if TX_ACTIVE = '1' then
                            tx_dv_reg <= '0';
                        end if;
                        if TX_DONE = '1' and tx_done_prev = '0' then
                            byte_to_send <= adc_data1_reg(11 downto 4);
                            tx_dv_reg    <= '1';
                            state        <= SEND_D1_HIGH;
                        end if;

                    when SEND_D1_HIGH =>
                        if TX_ACTIVE = '1' then
                            tx_dv_reg <= '0';
                        end if;
                        if TX_DONE = '1' and tx_done_prev = '0' then
                            byte_to_send <= adc_data1_reg(3 downto 0) & "0000";
                            tx_dv_reg    <= '1';
                            state        <= SEND_D1_LOW;
                        end if;

                    when SEND_D1_LOW =>
                        if TX_ACTIVE = '1' then
                            tx_dv_reg <= '0';
                        end if;
                        if TX_DONE = '1' and tx_done_prev = '0' then
                            byte_to_send <= x"45"; -- 'E' end frame
                            tx_dv_reg    <= '1';
                            state        <= SEND_EOL;
                        end if;

                    when SEND_EOL =>
                        if TX_ACTIVE = '1' then
                            tx_dv_reg <= '0';
                        end if;
                        if TX_DONE = '1' and tx_done_prev = '0' then
                            state <= WAIT_TX_COMPLETE;
                        end if;

                    when WAIT_TX_COMPLETE =>
                        if TX_ACTIVE = '0' then
                            delay_counter <= 0;
                            state <= WAIT_DELAY;
                        end if;

                    when WAIT_DELAY =>
                        if delay_counter < interframe_delay then
                            delay_counter <= delay_counter + 1;
                        else
                            state <= IDLE;
                        end if;

                    when others =>
                        state <= IDLE;
                end case;
            end if;
        end if;
    end process;

end RTL;
